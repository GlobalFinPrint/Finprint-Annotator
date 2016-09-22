import cv2
import time
import numpy as np
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
from queue import *
from config import global_config

from threading import Thread, Event, Lock

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
        self.shutdown_event = Event()
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

DEFAULT_BUFFER_SIZE = 60


class FrameManager(object):
    def __init__(self, file_name):
        super(FrameManager, self).__init__()
        self._capture = cv2.VideoCapture(file_name)
        if not self._capture.isOpened():
            raise Exception("Could not open file")
        self._capture_lock = Lock()

        b = global_config.get('VIDEOS', 'buffer_size')
        if b is None:
            self._buffer_size = DEFAULT_BUFFER_SIZE
        else:
            self._buffer_size = int(b)

        self.FPS = self._capture.get(cv2.CAP_PROP_FPS)
        self.playback_FPS = self.FPS
        self.height = self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.width = self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.count = self._capture.get(cv2.CAP_PROP_FRAME_COUNT)

        getLogger('finprint').debug("FPS {0}".format(self.FPS))
        getLogger('finprint').debug("frame height {0}".format(self.height))
        getLogger('finprint').debug("frame width {0}".format(self.width))
        getLogger('finprint').debug("buffer size {0}".format(self._buffer_size))

        self._buffer = Queue()
        self._quit = False
        self.thread = Thread(group=None, target=self._start_buffer, daemon=True)
        self.thread.start()
        self._last_frame_no = 0 # Relative to file reader
        self.current_pos = 0 # Relative to client
        self.current_frame_no = 0 # Relative to client

    def _start_buffer(self):
        time.sleep(1)
        buffer_time = time.perf_counter()
        while not self._quit:
            #print("qsize: {0}".format(self._frame_buffer.qsize()))
            if self._buffer.qsize() < self._buffer_size:

                with self._capture_lock:
                    self._load_frame()

                t = time.perf_counter()
                diff = t - buffer_time
                buffer_time = t
                #print("buffer grab diff {0:.4f}".format(diff))

            else:
                time.sleep(0.01)

    def _load_frame(self, current=False):
        if current:
            grabbed, frame = self._capture.retrieve()
        else:
            grabbed, frame = self._capture.read()
        ms_pos = self._capture.get(cv2.CAP_PROP_POS_MSEC)
        frame_pos = self._capture.get(cv2.CAP_PROP_POS_FRAMES)

        if grabbed:
            getLogger('finprint').debug("buffering frame {0:.1f} ms {1} frame".format(ms_pos, frame_pos))
            self._buffer.put((ms_pos, frame_pos, frame))
            self._last_frame_no = frame_pos

    def get_current_frame(self):
        return self._capture.retrieve()

    def get_next_frame(self):
        try:
            frame_time = time.perf_counter()
            # if self._buffer.qsize() < FrameManager.BUFFER_SIZE:
            #     time.sleep(2)
            ms_pos, frame_pos, frame = self._buffer.get(timeout=5)
            str = "getting frame "

            #print("{0} {1:.1f} ms {2} frame in {3:.4f} ms".format(str, ms_pos, frame_pos, time.perf_counter() - frame_time))
        except Empty as e:
            print("empty buffer")
            return False, None

        self.current_pos = ms_pos
        self.current_frame_no = frame_pos
        return True, frame

    def get_position(self):
        return self.current_pos

    def set_position(self, pos):
        getLogger('finprint').debug("setting position: {0}".format(pos))
        with self._capture_lock:
            self._capture.set(cv2.CAP_PROP_POS_MSEC, pos)
            self._buffer = Queue()
            self._load_frame(current=True)


class CvVideoWidget(QWidget):
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

        self._frame_manager = None

        self._dragging = False
        self._highlighter = Highlighter()
        self._onPositionChange = onPositionChange
        self.last_time = time.perf_counter()
        self._image = QImage(VIDEO_WIDTH, VIDEO_HEIGHT, QImage.Format_RGB888)
        self._image.fill(Qt.black)

        self._aspect_ratio = 0.0

        self._timer_flag = False
        self._timer = RepeatingTimer(0.0416) # 24 fps is GoPro norm
        self._timer.timerElapsed.connect(self.on_timer)

        self._last_progress = 0

        self._context_menu = None
        self._current_set = None

        self.setStyleSheet('QMenu { background-color: white; }')

    def load_set(self, set):
        self._current_set = set
        self._context_menu = ContextMenu(set, parent=self)
        self._context_menu.itemSelected.connect(self.onMenuSelect)

    def onMenuSelect(self, optDict):
        if optDict is not None:
            optDict['event_time'] = int(self.get_position())
            optDict['extent'] = self.get_highlight_extent().to_wkt()
            optDict['set'] = self._current_set
            d = EventDialog(parent=self)
            d.finished.connect(self.clear_extent)
            x = self.rect().right() + d.width() + 15
            y = self.rect().top() + 75
            print("Send dialog to {0}, {1}".format(x, y))
            d.move(x, y)
            d.launch(optDict)
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


        try:
            self._frame_manager = FrameManager(self._file_name)
        except Exception as ex:
            getLogger('finprint').exception("Exception loading video {0}: {1}".format(self._file_name, ex))
            return False

        self._play_state = PlayState.Paused

        self._aspect_ratio = self._frame_manager.width / self._frame_manager.height

        if not self._fullscreen:
            self.setFixedSize(self._target_width(), self._target_height())

        getLogger('finprint').debug("FPS {0}".format(self._frame_manager.FPS))
        getLogger('finprint').debug("frame height {0}".format(self._frame_manager.height))
        getLogger('finprint').debug("frame width {0}".format(self._frame_manager.width))
        getLogger('finprint').debug("aspect ratio {0}".format(self._aspect_ratio))
        getLogger('finprint').debug("target height {0}".format(self._target_height()))
        getLogger('finprint').debug("target width {0}".format(self._target_width()))
        getLogger('finprint').debug("target aspect ratio {0}".format(self._aspect_ratio))

        getLogger('finprint').debug("widget height {0}".format(self.height()))
        getLogger('finprint').debug("widget width {0}".format(self.width()))
        getLogger('finprint').debug("image height {0}".format(self._image.height()))
        getLogger('finprint').debug("image width {0}".format(self._image.width()))

        # don't start listening for spacebar until video is loaded and playable
        QCoreApplication.instance().installEventFilter(self)

        # Base line for measuring frame rate
        self.last_time = time.perf_counter()
        self._timer.interval = 1 / self._frame_manager.FPS #Set the timer to the frame rate of the video
        self._timer.start()

        self.set_position(0)
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
        if not self._timer_flag:
            self._timer_flag = True
            if self._play_state == PlayState.Playing:
                pos = self.get_position()
                if pos - self._last_progress > PROGRESS_UPDATE_INTERVAL:
                    self._last_progress = pos
                    self.progressUpdate.emit(pos)
                self.load_frame()
            elif self._play_state == PlayState.SeekForward:
                self.load_frame()
            elif self._play_state == PlayState.SeekBack:
                self.load_frame()

            self.update()
            self._timer_flag = False

    def clear(self):
        self._timer.cancel()
        if self._capture is not None:
            self._capture.release()
        self._image = QImage(self._target_width(), self._target_height(), QImage.Format_RGB888)
        self._image.fill(Qt.black)
        self.update()

    def _build_image(self, frame):
        image = None
        try:
            # adjust brightness and saturation
            if (self.saturation > 0 or self.brightness > 0) and self._play_state == PlayState.Paused:
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                h, s, v = cv2.split(hsv)
                final_hsv = cv2.merge((
                    h,
                    np.where(255 - s < self.saturation, 255, s + self.saturation),
                    np.where(255 - v < self.brightness, 255, v + self.brightness)
                ))
                frame = cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)

            # equalize contrast
            if self.contrast is True and self._play_state == PlayState.Paused:
                lab = cv2.cvtColor(frame, cv2.COLOR_BGR2Lab)
                l_chan = cv2.extractChannel(lab, 0)
                l_chan = cv2.createCLAHE(clipLimit=4).apply(l_chan)
                cv2.insertChannel(l_chan, lab, 0)
                frame = cv2.cvtColor(lab, cv2.COLOR_Lab2BGR)

            height, width, channels = frame.shape
            image = QImage(frame, width, height, QImage.Format_RGB888)
            image = image.scaled(self._target_width(), self._target_height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image = image.rgbSwapped()

        except Exception as ex:
            getLogger('finprint').exception('Exception building image')

        return image

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.drawImage(QPoint(0, 0), self._image)
        if self._play_state == PlayState.Paused:
            painter.setPen(QPen(QBrush(Qt.green), 1, Qt.SolidLine))
            painter.drawRect(self._highlighter.get_rect())

    def load_frame(self):
        self.last_time = time.perf_counter()
        grabbed, frame = self._frame_manager.get_next_frame()
        if grabbed:
            self._image = self._build_image(frame)
            self._onPositionChange(self.get_position())
        else:
            # Hit the end
            self._play_state = PlayState.EndOfStream
            self.playStateChanged.emit(self._play_state)

    def get_highlight_extent(self):
        ext = Extent()
        ext.setRect(self._highlighter.get_rect(), self._image.height(), self._image.width())
        return ext

    def get_highlight_as_list(self):
        r = self._highlighter.get_rect()
        return list(r.getCoords())

    def display_event(self, pos, extent):
        rect = extent.getRect(self._image.height(), self._image.width())
        self._highlighter.start_rect(rect.topLeft())
        self._highlighter.set_rect(rect.bottomRight())
        self.set_position(pos)
        self.repaint()

    def jump_back(self, seconds):
        self.clear_extent()
        pos = self.get_position() - seconds * 1000
        if pos < 0:
            pos = 0
        self.set_position(pos)

    def set_position(self, pos):
        self._frame_manager.set_position(pos)
        self.load_frame()
        self._onPositionChange(self.get_position())

    def mousePressEvent(self, event):
        self.pause()
        self._highlighter.start_rect(event.pos())
        self.update()

    def mouseMoveEvent(self, event):
        if self.paused():
            self._dragging = True
            x, y = event.pos().x(), event.pos().y()
            clamped_pos = QPoint(min(x, self._target_width()), min(y, self._target_height()))
            self._highlighter.set_rect(clamped_pos)
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
        self.playStateChanged.emit(self._play_state)
        self.playbackSpeedChanged.emit(0.0)
        if self.saturation > 0 or self.brightness > 0 or self.contrast is True:
            self.refresh_frame()

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
        if self._play_state == PlayState.EndOfStream:
            self.set_position(0)
        self._timer.interval = 1 / self._frame_manager.FPS

        self._frame_manager.playback_FPS = self._frame_manager.FPS
        self.playbackSpeedChanged.emit(1.0)

        self._play_state = PlayState.Playing
        self.clear_extent()
        self.playStateChanged.emit(self._play_state)

    def paused(self):
        return self._play_state == PlayState.Paused

    def get_position(self):
        return self._frame_manager.get_position()

    def get_length(self):
        if self._frame_manager.FPS == 0 or self._frame_manager.count == 0:
            getLogger('finprint').exception("Failed to calculate length")
            return 0
        else:
            return (self._frame_manager.count / self._frame_manager.FPS) * 1000  # Returns milliseconds as a float

    def fast_forward(self):
        self.set_speed(2.0)

    ## No worky.
    def rewind(self):
        if self._play_state == PlayState.SeekBack:
            self.pause()
        else:
            self._timer.interval = SEEK_CLOCK_FACTOR / self._frame_manager.FPS
            self._play_state = PlayState.SeekBack
            self.clear_extent()
        self.playStateChanged.emit(self._play_state)

    def context_menu(self):
        if self._context_menu:
            self._context_menu.display()

    def step_back(self):
        if not self.paused():
            self.pause()
        self.set_position(self.get_position() - FRAME_STEP * 3)

    def step_forward(self):
        if not self.paused():
            self.pause()
        self.set_position(self.get_position() + FRAME_STEP)

    def clear_extent(self):
        self._highlighter.clear()

    def set_speed(self, speed):
        self.clear_extent()
        self._frame_manager.playback_FPS = speed * self._frame_manager.FPS
        self._timer.interval = 1 / self._frame_manager.playback_FPS

        getLogger('finprint').debug('set playback speed to {}x'.format(speed))
        getLogger('finprint').debug('new FPS: {}'.format(self._frame_manager.playback_FPS))

        self.playbackSpeedChanged.emit(speed)

        if self._play_state != PlayState.SeekForward:
            self._play_state = PlayState.SeekForward
            self.playStateChanged.emit(self._play_state)

    def refresh_frame(self):
        self._frame_manager.set_position(self._frame_manager.get_position())
        self.load_frame()

    def resizeEvent(self, ev):
        if self._frame_manager is not None:
            self.refresh_frame()
