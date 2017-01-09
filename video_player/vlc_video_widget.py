import time
import psutil
from io import BytesIO
# XXX opencv filtering for now. Planning on switching to skimage
# for more image filtering possibilities in the future
# import cv2
import numpy as np

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
        self.can_update = True
        self.initUI()

    def initUI(self):
        self.show()

    def clear(self):
        self.curr_image = None
        self.highlighter.clear()

    def clearExtent(self):
        self.highlighter.clear()

    def set_rect(self, rect):
        self.highlighter.set_rect(rect)
        self.repaint()

    def get_rect(self):
        return self.highlighter.get_rect()

    def mousePressEvent(self, event):
        if self.can_update:
            self.highlighter.start_rect(event.pos())
            self.update()

    def mouseMoveEvent(self, event):
        if self.can_update:
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
        self._extent_rect = None
        self._duration = 0
        # XXX hacks for image filtering
        self.current_snapshot = None
        self.saturation = 0
        self.brightness = 0
        self.contrast = False

        # We will pass a window handle to libvlc, which
        # will be responsible for the actual rendering of the video
        if sys.platform == "darwin":  # for MacOS
            self.videoframe = QMacCocoaViewContainer(0)
        else:
            self.videoframe = QFrame()

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

        # bind instance to load libvlc. This is where we pass parameters for
        # buffering and the like.
        # XXX TODO - Make this configurable
        self.instance = Instance('--file-caching=10000')
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

        # current observation rect to display
        self._observation_rect = None

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

    # listen for any spacebar or mousedown event for play/pause
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

        # Where the magic starts - you have to give the handle of the QFrame (or similar object) to
        # vlc, different platforms have different functions for this. Downside is its opaque to you,
        # libvlc is doing the rendering, so you are limited in what you can do with the widget - it
        # is an event black hole in Windows platforms
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

        # wire up callbacks to VLC for snapshots and end of stream,
        # which is relative to the media being played
        mp_event_mgr = self.mediaplayer.event_manager()
        mp_event_mgr.event_attach(EventType.MediaPlayerSnapshotTaken, self.snapShotTaken)
        # XXX Uncomment these for debugging
        # mp_event_mgr.event_attach(EventType.MediaPlayerEndReached, self.streamEndEvent)
        # mp_event_mgr.event_attach(EventType.MediaPlayerPositionChanged, self.positionChangedEvent)
        # mp_event_mgr.event_attach(EventType.MediaPlayerTimeChanged, self.timeChangedEvent)

        # don't start listening for spacebar until video is loaded and playable
        self.mediaplayer.video_set_mouse_input(False)

        self._timer.start()

        # XXX hack to display the first few frames, which alters the bahavior of
        # VLC with respect to video scrubbing
        self.mediaplayer.set_time(20)
        self.mediaplayer.play()
        QTimer.singleShot(500, self.mediaplayer.pause)

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

    # Reinstate last_progress here
    def on_timer(self):
        if self._play_state is not PlayState.EndOfStream:
            pos = self.get_position()
            if pos > (self.media.get_duration() - 2000):
                self.streamEndEvent()
            if pos - self._last_progress > PROGRESS_UPDATE_INTERVAL:
                self._last_progress = pos
                self.progressUpdate.emit(pos)
            self._onPositionChange(self.get_position())

    def clear(self):
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
        rect = extent.getRect(self.videoframe.height(), self.videoframe.width())
        self._observation_rect = rect
        self.scrub_position(pos)
        QTimer.singleShot(1000, self.display_observation_snaphot)

    def take_videoframe_snapshot(self):
        getLogger('finprint').info('take videoframe snapshot')
        self.annotationImage.clear()
        pix = QPixmap.grabWindow(self.videoframe.winId())
        snap = pix.scaledToHeight(self.videoframe.height())
        self.annotationImage.curr_image = snap.toImage()
        self.current_snapshot = snap.toImage()
        # XXX inline this function
        if self.is_filtered():
            self.refresh_frame()
        self.setCurrentIndex(ANNOTATION_INDEX)

    def display_observation_snaphot(self):
        self.take_videoframe_snapshot()
        if self._observation_rect is not None:
            getLogger('finprint').info('draw observation rect at {0}'.format(self._observation_rect))
            self.annotationImage.highlighter.start_rect(self._observation_rect.topLeft())
            self.annotationImage.highlighter.set_rect(self._observation_rect.bottomRight())
            self.annotationImage.repaint()

    def jump_back(self, seconds):
        self.clear_extent()
        time_back = self.mediaplayer.get_time() - seconds * 1000
        pos_back = time_back/self.media.get_duration()
        if time_back < 0:
            time_back = 0
        # if paused, swap out the static image
        self.mediaplayer.set_position(pos_back)
        if self._play_state is PlayState.Paused:
            self.setCurrentIndex(VIDEOFRAME_INDEX)
            self._onPositionChange(self.get_position())

    def scrub_position(self, pos):
        # todo - just have a Seek State
        self._play_state = PlayState.Paused
        p = (pos) / self.media.get_duration()
        getLogger('finprint').info('scrub_position {0}'.format(p))
        self.setCurrentIndex(VIDEOFRAME_INDEX)
        self.mediaplayer.set_position(p)

    def set_position(self, pos):
        self._onPositionChange(pos)
        p = (pos) / self.media.get_duration()
        getLogger('finprint').info('set_position {0}'.format(p))
        self.setCurrentIndex(VIDEOFRAME_INDEX)
        self.mediaplayer.set_position(p)
        self.take_videoframe_snapshot()

    def toggle_play(self):
        if self._play_state in [PlayState.Paused, PlayState.SeekForward, PlayState.SeekBack]:
            getLogger('finprint').info('toggle_play: play')
            self.play()
        else:
            getLogger('finprint').info('toggle_play: pause')
            self.pause()
            self.take_videoframe_snapshot()

    def pause(self):
        if self.mediaplayer.is_playing():
            self.mediaplayer.pause()
        getLogger('finprint').info('paused')
        self._play_state = PlayState.Paused
        self.playStateChanged.emit(self._play_state)
        self.playbackSpeedChanged.emit(0.0)

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
        self.clear_extent()
        self.set_speed(1.0)
        self.mediaplayer.play()
        self._play_state = PlayState.Playing
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

    def is_filtered(self):
        return self.saturation > 0 or self.brightness > 0 or self.contrast

    def clear_extent(self):
        self.annotationImage.clearExtent()

    def set_speed(self, speed, start_playing = True):
        # XXX assume we are about to or are playing, so show videoframe
        self.setCurrentIndex(VIDEOFRAME_INDEX)
        self.mediaplayer.set_rate(speed)

        # XXX Hack for set_positon
        if start_playing:
            self.playbackSpeedChanged.emit(speed)

        if PlayState.Paused and start_playing:
            self.mediaplayer.play()
            self._play_state = PlayState.Playing
            self.playStateChanged.emit(self._play_state)

    def resizeEvent(self, ev):
        self.update()

    def refresh_frame(self):
        self._refresh_frame_cv()

    def _refresh_frame_cv(self):
        if self._play_state is PlayState.Paused:
            # grab a cv representation of the image
            # that has not been filtered
            # curr_img = self.current_snapshot
            # cvFrame = self.qImageToNumpy(curr_img)
            # filtered_img = self.filter_image(cvFrame)
            # self.annotationImage.curr_image = filtered_img
            self.update()

    def qImageToNumpy(self, curr_image):
        curr_image = curr_image.convertToFormat(QImage.Format_RGB888)
        curr_image = curr_image.rgbSwapped()
        width = curr_image.width()
        height = curr_image.height()

        ptr = curr_image.bits()
        ptr.setsize(curr_image.byteCount())
        # XXX Make the # of channels (shape[2]) conditional, so if we have an alpha or b/w
        frame = np.array(ptr).reshape(height, width, 3)  # Copies the data
        return frame

    # XXX TODO - When we go to skimage, use this to
    def numpyToQImage(self, im, copy=False):
        if im is None:
            return QImage()

        if len(im.shape) == 3:
            if im.shape[2] == 3:
                qim = QImage(im.data, im.shape[1], im.shape[0], im.strides[0], QImage.Format_RGB888)
                return qim.copy() if copy else qim
            elif im.shape[2] == 4:
                qim = QImage(im.data, im.shape[1], im.shape[0], im.strides[0], QImage.Format_ARGB32)
                return qim.copy() if copy else qim

        return QImage()

    # XXX TODO - Move this over to skimage, so that we can have more
    # possibilities in histogram manipulation
    def filter_image(self, curr_img):
        pass
        # frame = curr_img
        # image = None
        # try:
        #     getLogger('finprint').debug('saturation: {0}  brightness: {1}'.format(self.saturation, self.brightness))
        #     # adjust brightness and saturation
        #     if (self.saturation > 0 or self.brightness > 0) and self._play_state == PlayState.Paused:
        #         hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        #         h, s, v = cv2.split(hsv)
        #         final_hsv = cv2.merge((
        #             h,
        #             np.where(255 - s < self.saturation, 255, s + self.saturation),
        #             np.where(255 - v < self.brightness, 255, v + self.brightness)
        #         ))
        #         frame = cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)
        #
        #     # equalize contrast
        #     if self.contrast is True and self._play_state == PlayState.Paused:
        #         lab = cv2.cvtColor(frame, cv2.COLOR_BGR2Lab)
        #         l_chan = cv2.extractChannel(lab, 0)
        #         l_chan = cv2.createCLAHE(clipLimit=2.0).apply(l_chan)
        #         cv2.insertChannel(l_chan, lab, 0)
        #         frame = cv2.cvtColor(lab, cv2.COLOR_Lab2BGR)
        #
        #     height, width, channels = frame.shape
        #     image = QImage(frame, width, height, QImage.Format_RGB888)
        #
        # except Exception as ex:
        #     getLogger('finprint').exception('Exception building image: {}'.format(str(ex)))
        #
        # return image

    # callbacks start here
    # XXX TODO - add a video filter to libvlc to detect when video has been clicked,
    # so that it acts like the previous opencv-based version. This is likely a c based
    # video filter (plugin) for libvlc.
    def playerPausedEvent(self, event):
        # XXX remove
        getLogger('finprint').info('player paused event')

    # emit an event when at end of video.
    def streamEndEvent(self):
        getLogger('finprint').info('end of stream event')
        self._play_state = PlayState.EndOfStream
        self.playStateChanged.emit(self._play_state)
        dur = self.media.get_duration()
        self.mediaplayer.set_position((dur - 1000)/dur)
        self.pause()
        self.playStateChanged.emit(self._play_state)


    # once a snaphsot is generated by vlc, post the snapshot (a decoded video frame)
    # in a background thread. It seems to be blocking on the main thread, even though
    # we should be running off of a C runtime thread
    def snapShotTaken(self, event):
        getLogger('finprint').info('process snaphot')
        # upload on a separate thread
        QTimer.singleShot(50, self.process_snapshot)

    def process_snapshot(self):
        if self.curr_s3_upload is not None:
            s3_filename = os.path.basename(self.curr_s3_upload)
            getLogger('finprint').info('Searching for {0}'.format(s3_filename))
            expected_file = os.path.join(self.temp_snapshot_dir, s3_filename)
            if os.path.isfile(expected_file):
                getLogger('finprint').info('Found {0}'.format(expected_file))
                upload_img = QImage(expected_file)
                self.upload_image(self.curr_s3_upload, upload_img)
                self.curr_s3_upload = None
                os.remove(expected_file)

    # callback for 'MediaPlayerPositionChanged'
    def positionChangedEvent(self, event):
        pos = self.mediaplayer.get_position()
        getLogger('finprint').info('Position changed: {0}'.format(pos))

    # callback for 'MediaPlayerTimeChanged'
    def timeChangedEvent(self, event):
        pos = self.mediaplayer.get_time()
        getLogger('finprint').info('Time changed: {0}'.format(pos))
