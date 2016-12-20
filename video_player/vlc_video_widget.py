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
from tempfile import gettempdir
from .vlc import *


PROGRESS_UPDATE_INTERVAL = 30000
VIDEO_WIDTH = 800  # make this more adjustable
VIDEO_HEIGHT = 450
DEFAULT_ASPECT_RATIO = 16.0/9.0
AWS_BUCKET_NAME = 'finprint-annotator-screen-captures'
SCREEN_CAPTURE_QUALITY = 25  # 0 to 100 (inclusive); lower is small file, higher is better quality
FRAME_STEP = 50
TEMP_SNAPSHOT_DIR = 'finprint-snapshot'

SEEK_CLOCK_FACTOR = 30
SEEK_FRAME_JUMP = 60

VIDEOFRAME_INDEX = 0
ANNOTATION_INDEX = 1

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
        self.highlighter = Highlighter()
        self._dragging = False
        self.curr_image = None
        self.initUI()

    def initUI(self):
        self.show()

    def clear(self):
        self.curr_image = None
        self.highlighter.clear()

    def get_rect(self):
        return self.highlighter.get_rect()

    def mousePressEvent(self, event):
        self.highlighter.start_rect(event.pos())
        self.update()

    def mouseMoveEvent(self, event):
        self._dragging = True
        x, y = event.pos().x(), event.pos().y()
        clamped_pos = QPoint(min(x, self.width()), min(y, self.height()))
        self.highlighter.set_rect(clamped_pos)
        self.update()

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            self.update()
            self.parent().context_menu()

    def paintEvent(self, e):
        # This should only be called when
        if self.curr_image is not None:
            painter = QPainter()
            painter.begin(self)
            painter.drawImage(QPoint(0, 0), self.curr_image)
            painter.setPen(QPen(QBrush(Qt.green), 1, Qt.SolidLine))
            painter.drawRect(self.highlighter.get_rect())
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

        # We will pass a window handle to libvlc, which
        # will be responsible for the actual rendering of the video
        if sys.platform == "darwin":  # for MacOS
            self.videoframe = QMacCocoaViewContainer(0)
        else:
            #self.videoframe = QWidget()
            self.videoframe = QGraphicsView()

        # add the videoframe
        self.addWidget(self.videoframe)

        # XXX Fixme - this is a hack
        if not self._fullscreen:
            self.setMinimumSize(VIDEO_WIDTH, VIDEO_HEIGHT)
            self.setMaximumSize(VIDEO_WIDTH, VIDEO_HEIGHT)

        # add the annotation image
        self.annotationImage = AnnotationImage()
        self.addWidget(self.annotationImage)

        # set videoframe as default visibile widget
        self.setCurrentIndex(VIDEOFRAME_INDEX)

        # XXX todo - get aspect ratio from vlc when played
        self._aspect_ratio = DEFAULT_ASPECT_RATIO

        # temporary storage for vlc snapshots
        self.temp_snapshot_dir = os.path.join(gettempdir(), TEMP_SNAPSHOT_DIR)
        if not os.path.exists(self.temp_snapshot_dir):
            os.makedirs(self.temp_snapshot_dir)

        # bind instance to load libvlc
        self.instance = Instance()
        # create a vlc media player from loaded library
        self.mediaplayer = self.instance.media_player_new()

        # This keeps track of how far the annotator has gotten in the video
        self._last_progress = 0

        self._timer_flag = False
        self.timer_time = time.perf_counter()
        self._timer = RepeatingTimer(0.25)
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

    # XXX what are the use of sets
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

    # listen for any spacebar or mousedown event for play/pause
    def eventFilter(self, obj, evt):
        if evt.type() == QEvent.MouseButtonPress:
            print(evt.pos())
            self.toggle_play()
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
        # libvlc is doing the rendering, so you are limited in what you can do with the widget
        if sys.platform.startswith('linux'):  # for Linux using the X Server
            self.mediaplayer.set_xwindow(self.videoframe.winId())
        elif sys.platform == "win32":  # for Windows
            self.mediaplayer.set_hwnd(self.videoframe.winId())
        elif sys.platform == "darwin":  # for MacOS
            self.mediaplayer.set_nsobject(self.videoframe.winId())

        # don't start listening for spacebar until video is loaded and playable
        QCoreApplication.instance().installEventFilter(self)

        self._play_state = PlayState.Paused

        self._aspect_ratio = self.videoframe.width() / self.videoframe.height()

        # XXX TODO - wire up callbacks to VLC for when paused and end of stream
        mp_event_mgr = self.mediaplayer.event_manager()
        mp_event_mgr.event_attach(EventType.MediaPlayerSnapshotTaken, self.snapShotTaken)
        mp_event_mgr.event_attach(EventType.MediaPlayerEndReached, self.streamEndEvent)

        # don't start listening for spacebar until video is loaded and playable
        self.mediaplayer.video_set_mouse_input(False)

        self._timer.start()

        self.mediaplayer.set_time(0)

        return True

    # XXX TODO add support for moving between observation markers. Because of the whole stacked widget design,
    # it means showing the videoframe widget, moving the timeline on the videoplayer, and then taking another snapshot,
    # show the annotation image and applying the extent rectangle. But, maybe you can just just set position, and draw
    # on the videoframe itself.

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

    # Reinstate last_progress here
    def on_timer(self):
        if self._play_state in [PlayState.Playing, PlayState.SeekForward, PlayState.SeekBack] :
            ts = self.mediaplayer.get_time()
            self.progressUpdate.emit(ts)
            self._onPositionChange(self.get_position())

    def clear(self):
        # XXX TODO
        # self._profile_timer.cancel()
        self._timer.cancel()
        self.update()

    def get_highlight_extent(self):
        ext = Extent()
        ext.setRect(self.annotationImage.get_rect(), self.videoframe.height(), self.videoframe.width())
        return ext

    def get_highlight_as_list(self):
        r = self._highlighter.get_rect()
        return list(r.getCoords())

    def display_event(self, pos, extent):
        self.annotationImage.clear()
        self.move_to_position(pos)
        #XXX todo - add a graphics scene here to fix the overlay
        #self.take_videoframe_snapshot()
  #      self.update()
  #       rect = extent.getRect(self.videoframe.height(), self.videoframe.width())
  #       self.annotationImage.highlighter.start_rect(rect.topLeft())
  #       self.annotationImage.highlighter.set_rect(rect.bottomRight())

    def take_videoframe_snapshot(self):
        pix = QPixmap.grabWindow(self.videoframe.winId())
        self.annotationImage.curr_image = pix.toImage()
        self.setCurrentIndex(ANNOTATION_INDEX)

    # XXX This is used for displaying existing observations
    def move_to_position(self, pos):
        # if not playing, we need to switch to showing
        # the videoframe
        self.set_speed(.25)
        self.mediaplayer.play()
        time.sleep(.15)
        self.mediaplayer.set_time(pos)
        self.mediaplayer.pause()
        self._play_state = PlayState.Paused
        self.playStateChanged.emit(self._play_state)
        self.update()

    def jump_back(self, seconds):
        self.clear_extent()
        time_back = self.mediaplayer.get_time() - seconds * 1000
        if time_back < 0:
            time_back = 0
        self.mediaplayer.set_time(time_back)

    def set_position(self, pos):
        self.move_to_position(pos)
        self._onPositionChange(pos)
        self._play_state = PlayState.Paused


    def toggle_play(self):
        if self._play_state in [PlayState.Paused, PlayState.EndOfStream]:
            self.play()
        else:
            self.pause()

    def pause(self):
        # first, pause the player, and notify state change
        self._play_state = PlayState.Paused
        self.mediaplayer.pause()
        self.playStateChanged.emit(self._play_state)
        self.playbackSpeedChanged.emit(0.0)
        self.take_videoframe_snapshot()
        # XXX TODO - fix the saturation and brightness using VLC.
        # if self.saturation > 0 or self.brightness > 0 or self.contrast is True:
        #     self.refresh_frame()

    def save_image(self, filename):
        self.curr_s3_upload = filename
        curr_snapshot = os.path.basename(filename)
        snapshot_path_bytes = os.path.join(self.temp_snapshot_dir, curr_snapshot).encode('utf-8')
        # vlc calls need a C style string
        snapshot_path = ctypes.create_string_buffer(snapshot_path_bytes)
        # request actual decoded frame size from libvlc
        self.mediaplayer.video_take_snapshot(0, snapshot_path, 0, 0)

    def upload_image(self, filename, curr_image):
        getLogger('finprint').info('Uploading {0}'.format(filename))
        data = QByteArray()
        buffer = QBuffer(data)
        curr_image.save(buffer, 'PNG', SCREEN_CAPTURE_QUALITY)
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
        # TODO emit if end of stream via callback
        self.setCurrentIndex(VIDEOFRAME_INDEX)
        self.set_speed(1.0)
        self.mediaplayer.play()
        self._play_state = PlayState.Playing
        self.clear_extent()
        self.playStateChanged.emit(self._play_state)

    def is_paused(self):
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
        if not self.is_paused():
            self.pause()
        self.set_position(self.get_position() - FRAME_STEP)

    def step_forward(self):
        if not self.is_paused():
            self.pause()
        self.set_position(self.get_position() + FRAME_STEP)

    def clear_extent(self):
        self.annotationImage.clear()

    def set_speed(self, speed):
        self.mediaplayer.set_rate(speed)
        self.playbackSpeedChanged.emit(speed)

        if self._play_state is PlayState.Paused:
            self.mediaplayer.play()
            self._play_state = PlayState.SeekForward
            self.playStateChanged.emit(self._play_state)

    def resizeEvent(self, ev):
        self.update()

    def eventFilter(self, obj, evt):
        if evt.type() == QEvent.KeyPress and obj.__class__ != QLineEdit and QApplication.activeModalWidget() is None:
            if evt.key() == Qt.Key_Space:
                self.toggle_play()
                return True
        return False

    ## callbacks start here
    # XXX TODO - add a video filter to libvlc to detect when video has been clicked
    def playerPausedEvent(self, event):
        print("playerPaused:", event.type, event.u)

    # emit an event when at end of video.
    def streamEndEvent(self, event):
        print("streamEndEvent callback:", event.type, event.u)
        self._play_state = PlayState.EndOfStream
        self.playStateChanged.emit(self._play_state)

    # once a snaphsot is generated by vlc, post the snapshot (a decoded video frame)
    def snapShotTaken(self, event):
        getLogger('finprint').info('Snapshot callback event')
        if self.curr_s3_upload is not None:
            s3_filename = os.path.basename(self.curr_s3_upload)
            print('Searching for {0}'.format(s3_filename))
            getLogger('finprint').info('Searching for {0}'.format(s3_filename))
            expected_file = os.path.join(self.temp_snapshot_dir, s3_filename)
            if os.path.isfile(expected_file):
                print('Found {0}'.format(expected_file))
                getLogger('finprint').info('Found {0}'.format(expected_file))
                upload_img = QImage(expected_file)
                self.upload_image(self.curr_s3_upload, upload_img)
                self.curr_s3_upload = None
                os.remove (expected_file)


