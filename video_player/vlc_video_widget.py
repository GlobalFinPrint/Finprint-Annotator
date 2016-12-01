import time
import psutil
from io import BytesIO
from boto.s3.connection import S3Connection
from boto.exception import S3ResponseError
from logging import getLogger
from global_finprint import Extent
from .play_state import PlayState
from .highlighter import Highlighter
from .context_menu import ContextMenu, EventDialog
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from config import global_config
from threading import Thread
from threading import Event as PyEvent
from .vlc import *


PROGRESS_UPDATE_INTERVAL = 30000
VIDEO_WIDTH = 800  # make this more adjustable
VIDEO_HEIGHT = 450
AWS_BUCKET_NAME = 'finprint-annotator-screen-captures'
SCREEN_CAPTURE_QUALITY = 25  # 0 to 100 (inclusive); lower is small file, higher is better quality
FRAME_STEP = 50

SEEK_CLOCK_FACTOR = 30
SEEK_FRAME_JUMP = 60

creds = open('./credentials.csv').readlines()[1].split(',')
AWS_ACCESS_KEY_ID = creds[1].strip()
AWS_SECRET_ACCESS_KEY = creds[2].strip()


class RepeatingTimer(QObject):
    timerElapsed = pyqtSignal()

    def __init__(self, interval):
        super(RepeatingTimer, self).__init__()
        self.interval = interval
        self.active = False
        self.shutdown_event = PyEvent()
        self.thread = None

    def wrapper_function(self):
        self.active = True
        self.shutdown_event.clear()
        while self.active:
            if self.shutdown_event.wait(timeout=self.interval):
                self.active = False
            else:
                self.timerElapsed.emit()

    def start(self):
        self.thread = Thread(group=None, target=self.wrapper_function, daemon=True)
        self.thread.start()

    def cancel(self):
        self.shutdown_event.set()


class AnnotationImage(QWidget):

    def __init__(self):
        QWidget.__init__(self)
        self._highlighter = Highlighter()
        self.dragging = False
        self.curr_image = None
        self.initUI()

    def initUI(self):
        self.show()

    def clear(self):
        self._timer.clear()
        self.curr_image = None
        self._highlighter.clear()

    def mousePressEvent(self, event):
        self._highlighter.start_rect(event.pos())
        self.update()

    def mouseMoveEvent(self, event):
        self._dragging = True
        x, y = event.pos().x(), event.pos().y()
        clamped_pos = QPoint(min(x, self.width()), min(y, self.height()))
        self._highlighter.set_rect(clamped_pos)
        self.update()

    def paintEvent(self, e):
        # This should only be called when
        if self.curr_image is not None:
            painter = QPainter()
            painter.begin(self)
            painter.drawImage(QPoint(0, 0), self.curr_image)
            painter.setPen(QPen(QBrush(Qt.green), 1, Qt.SolidLine))
            painter.drawRect(self._highlighter.get_rect())
            painter.end()


class VlcVideoWidget(QStackedWidget):
    playStateChanged = pyqtSignal(PlayState)
    progressUpdate = pyqtSignal(int)
    playbackSpeedChanged = pyqtSignal(float)
    saturation = 0
    brightness = 0
    contrast = False

    def __init__(self, parent=None, onPositionChange=None, fullscreen=False):
        QWidget.__init__(self, parent)
        self._capture = None
        self._paused = True
        self._play_state = PlayState.NotReady
        self._file_name = None
        self._fullscreen = fullscreen
        self._dragging = False
        self._highlighter = Highlighter()
        self._onPositionChange = onPositionChange

        # We will pass A QFrame window handle to libvlc
        if sys.platform == "darwin":  # for MacOS
            self.videoframe = QMacCocoaViewContainer(0)
        else:
            self.videoframe = QFrame()

        self.addWidget(self.videoframe)
        # XXX Fixme - this is a hack
        self.setMinimumSize(VIDEO_WIDTH, VIDEO_HEIGHT)
        self.setMaximumSize(VIDEO_WIDTH, VIDEO_HEIGHT)

        # set videoframe as default visibile widget
        self.setCurrentIndex(0)
        # XXX todo - get aspect ratio from vlc
        self._aspect_ratio = 0.0

        # bind instance to load libvlc
        self.instance = Instance()
        # create a vlc media player from loaded library
        self.mediaplayer = self.instance.media_player_new()

        # XXX should this be removed?
        self._last_progress = 0

        # XXX Still need a timer to update the timeline display, may
        # want to move this into the layout widget, but for now, try
        # to honor the interface already in place
        self._timer_flag = False
        self.timer_time = time.perf_counter()
        self._timer = RepeatingTimer(0.125)
        self._timer.timerElapsed.connect(self.on_timer)

        self._context_menu = None
        self._current_set = None

        self.setStyleSheet('QMenu { background-color: white; }')

        # XXX Todo - move ui components into a initUI
        self.initUI()

    def initUI(self):
        pass

    def _print_sys_info(self):
        l = getLogger('finprint')
        p = psutil.Process()
        l.debug('System CPU %: {}'.format(psutil.cpu_percent()))
        l.debug('System Memory: {}'.format(psutil.virtual_memory()))
        l.debug('Process CPU %: {}'.format(p.cpu_percent()))
        l.debug('Process Threads: {}'.format(p.threads()))
        l.debug('Process Memory: {}'.format(p.memory_info()))
        l.debug('Process Memory %: {}'.format(p.memory_percent()))

    def load_set(self, set):
        self._current_set = set
        self._context_menu = ContextMenu(set, parent=self)
        self._context_menu.itemSelected.connect(self.onMenuSelect)

    def onMenuSelect(self, optDict):
        if optDict is not None:
            optDict['event_time'] = int(self.get_position())
            optDict['extent'] = self.get_highlight_extent().to_wkt()
            optDict['set'] = self._current_set
            diag = EventDialog(parent=self)
            diag.finished.connect(self.clear_extent)
            screen_center = QApplication.desktop().screenGeometry().center()
            x = screen_center.x() - diag.rect().center().x()
            y = screen_center.y() - 200
            getLogger('finprint').debug('Send dialog to {0}, {1}'.format(x, y))
            diag.move(x, y)
            diag.launch(optDict)
        else:
            self.clear_extent()

    # listen for any spacebar touches for play/pause
    def eventFilter(self, obj, evt):
        if evt.type() == QEvent.KeyPress and obj.__class__ != QLineEdit and QApplication.activeModalWidget() is None:
            if evt.key() == Qt.Key_Space:
                self.toggle_play()
                return True
        return False

    def load(self, file_name):
        self._file_name = file_name

        self.clear_extent()

        getLogger('finprint').info("Loading loading video {0}".format(self._file_name))
        self.media = self.instance.media_new(self._file_name)
        self.mediaplayer.set_media(self.media)
        self.media.parse()

        # todo - figure out if the file couldn't be parsed or loaded
        # getLogger('finprint').exception("Exception loading video {0}: {1}".format(self._file_name, ex))

        # Where the magic starts - you have to give the handle of the QFrame (or similar object) to
        # vlc, different platforms have different functions for this. Downside is its opaque to you,
        # libvlc is doing the rendering
        if sys.platform.startswith('linux'):  # for Linux using the X Server
            self.mediaplayer.set_xwindow(self.videoframe.winId())
        elif sys.platform == "win32":  # for Windows
            self.mediaplayer.set_hwnd(self.videoframe.winId())
        elif sys.platform == "darwin":  # for MacOS
            self.mediaplayer.set_nsobject(self.videoframe.winId())

        # XXX todo - we need mouse events in the video frame
        # self.mediaplayer.video_set_mouse_input(True)
        self.videoframe.setMouseTracking(True)

        self._play_state = PlayState.Paused

        self._aspect_ratio = self.videoframe.width() / self.videoframe.height()


        if not self._fullscreen:
            self.setFixedSize(self._target_width(), self._target_height())

        getLogger('finprint').debug("aspect ratio {0}".format(self._aspect_ratio))
        getLogger('finprint').debug("target height {0}".format(self._target_height()))
        getLogger('finprint').debug("target width {0}".format(self._target_width()))
        getLogger('finprint').debug("target aspect ratio {0}".format(self._aspect_ratio))

        getLogger('finprint').debug("widget height {0}".format(self.height()))
        getLogger('finprint').debug("widget width {0}".format(self.width()))
        #getLogger('finprint').debug("image height {0}".format(self._image.height()))
        #getLogger('finprint').debug("image width {0}".format(self._image.width()))


        # don't start listening for spacebar until video is loaded and playable
        QCoreApplication.instance().installEventFilter(self)

        self._timer.start()

        self.mediaplayer.set_position(0)

        return True

    def _target_width(self):
        try:
            if not self._fullscreen:
                return VIDEO_WIDTH
            elif self.geometry().width() / self.geometry().height() > self._aspect_ratio:
                return self._target_height() * self._aspect_ratio
            else:
                return self.geometry().width()
        except ZeroDivisionError:
            return 0

    def _target_height(self):
        try:
            if not self._fullscreen:
                return self._target_width() / self._aspect_ratio
            elif self.geometry().width() / self.geometry().height() < self._aspect_ratio:
                return self._target_width() / self._aspect_ratio
            else:
                return self.geometry().height()
        except ZeroDivisionError:
            return 0

    def on_timer(self):
        if self._play_state == PlayState.Playing:
            ts = self.mediaplayer.get_time()
            self.progressUpdate.emit(ts)
            self.update()

    def clear(self):
        # XXX TODO
        # self._profile_timer.cancel()

        self._timer.cancel()
        self.update()

    def get_highlight_extent(self):
        ext = Extent()
        ext.setRect(self._highlighter.get_rect(), self.videoframe.height(), self.videoframe.width())
        return ext

    def get_highlight_as_list(self):
        r = self._highlighter.get_rect()
        return list(r.getCoords())

    def display_event(self, pos, extent):
        # XXX I'm assuming this will also require capturing a still, and then drawing
        # over it. Right now we are just dealing with the videoframe
        rect = extent.getRect(self.videoframe.height(), self.videoframe.width())
        self._highlighter.start_rect(rect.topLeft())
        self._highlighter.set_rect(rect.bottomRight())
        self.mediaplayer.set_time(pos)
        self.repaint()

    def jump_back(self, seconds):
        self.clear_extent()
        time_back = self.mediaplayer.get_time() - seconds * 1000
        if time_back < 0:
            time_back = 0
        self.mediaplayer.set_time(time_back)

    def set_position(self, pos):
        self.mediaplayer.set_time(pos)
        self._onPositionChange(self.get_position())

    def mousePressEvent(self, event):
        self.pause()
        self._highlighter.start_rect(event.pos())
        self.update()

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            self.update()
            self.context_menu()

    def toggle_play(self):
        if self._play_state == PlayState.Paused or self._play_state == PlayState.EndOfStream:
            self.play()
        else:
            self.pause()

    def pause(self):
        self._play_state = PlayState.Paused
        self.mediaplayer.set_rate(1.0)
        self.mediaplayer.pause()
        self.playStateChanged.emit(self._play_state)
        self.playbackSpeedChanged.emit(0.0)
        # XXX TODO
        # if self.saturation > 0 or self.brightness > 0 or self.contrast is True:
        #     self.refresh_frame()

    # XXX fix me - need to read the file off the disk, and into the buffer
    def save_image(self, filename):
        data = QByteArray()
        buffer = QBuffer(data)
        self._image.save(buffer, 'PNG', SCREEN_CAPTURE_QUALITY)
        bio = BytesIO(data.data())
        bio.seek(0)
        try:
            conn = S3Connection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
            bucket = conn.get_bucket(AWS_BUCKET_NAME)
            if not bucket.get_key(filename):
                key = bucket.new_key(filename)
                key.set_contents_from_string(bio.read(), headers={'Content-Type': 'image/png'})
                key.set_acl('public-read')
            else:
                getLogger('finprint').error('File already exists on S3: {0}'.format(filename))
        except S3ResponseError as e:
            getLogger('finprint').error(str(e))

    def play(self):
        self.set_speed(1.0)
        self.mediaplayer.play()
        self._play_state = PlayState.Playing
        self.clear_extent()
        self.playStateChanged.emit(self._play_state)

    # XXX this is probably going to need to be
    def paused(self):
        return self._play_state == PlayState.Paused

    def get_position(self):
        return self.mediaplayer.get_time()

    def get_length(self):
        duration = self.media.get_duration()
        if duration == -1:
            getLogger('finprint').exception("Failed to calculate length")
            return 0
        else:
            return duration

    def fast_forward(self):
        self.set_speed(2.0)

    ## No worky.
    def rewind(self):
        if self._play_state == PlayState.SeekBack:
            self.mediaplayer.pause()
        else:
            self._play_state = PlayState.SeekBack
            self.clear_extent()
        self.playStateChanged.emit(self._play_state)

    def context_menu(self):
        if self._context_menu:
            self._context_menu.display()

    def step_back(self):
        if not self.paused():
            self.pause()
        self.set_position(self.get_position() - FRAME_STEP)
        # XXX ask why this was set to a multiple of 3
        # self.set_position(self.get_position() - FRAME_STEP * 3)


    def step_forward(self):
        if not self.paused():
            self.pause()
        self.set_position(self.get_position() + FRAME_STEP)

    def clear_extent(self):
        self._highlighter.clear()

    def set_speed(self, speed):
        self.clear_extent()

        self.mediaplayer.set_rate(speed)

        getLogger('finprint').debug('set playback speed to {}x'.format(speed))

        self.playbackSpeedChanged.emit(speed)

        if self._play_state != PlayState.SeekForward:
            self._play_state = PlayState.SeekForward
            self.mediaplayer.play()
            self.playStateChanged.emit(self._play_state)

    # def refresh_frame(self):
    #     self._frame_manager.set_position(self._frame_manager.get_position())
    #     self.load_frame()

    def resizeEvent(self, ev):
        self.update()
