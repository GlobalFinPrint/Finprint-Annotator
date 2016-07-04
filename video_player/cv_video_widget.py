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
from .context_menu import ContextMenu
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from threading import Thread, Event

PROGRESS_UPDATE_INTERVAL = 30000
VIDEO_WIDTH = 800  # make this more adjustable
VIDEO_HEIGHT = 450
AWS_BUCKET_NAME = 'finprint-annotator-screen-captures'
SCREEN_CAPTURE_QUALITY = 25  # 0 to 100 (inclusive); lower is small file, higher is better quality
FRAME_STEP = 50

creds = open('./credentials.csv').readlines()[1].split(',')
AWS_ACCESS_KEY_ID = creds[1].strip()
AWS_SECRET_ACCESS_KEY = creds[2].strip()

class RepeatingTimer():
   def __init__(self, interval, callback):
      self.interval = interval
      self.callback = callback
      self.active = False
      self.elapse_event = Event()
      self.thread = Thread(group=None, target=self.wrapper_function, daemon=True)

   def wrapper_function(self):
        self.active = True
        self.elapse_event.clear()
        timeout = self.interval
        while self.active:
            if self.elapse_event.wait(timeout=timeout):
                self.active = False
            else:
                t = time.perf_counter()
                self.callback()
                timeout = self.interval - (time.perf_counter() - t) #adjust for time spent in callback

   def start(self):
      self.thread.start()

   def cancel(self):
      self.elapse_event.set()


class CvVideoWidget(QWidget):
    playStateChanged = pyqtSignal(PlayState)
    progressUpdate = pyqtSignal(int)

    def __init__(self, parent=None, onPositionChange=None):
        QWidget.__init__(self, parent)
        self._capture = None
        self._paused = True
        self._play_state = PlayState.NotReady
        self._file_name = None

        self._dragging = False
        self._highlighter = Highlighter()
        self._onPositionChange = onPositionChange
        self.start_time = time.perf_counter()
        self.last_time = time.perf_counter()
        self._image = QImage(VIDEO_WIDTH, VIDEO_HEIGHT, QImage.Format_RGB888)
        self._image.fill(Qt.black)

        self._timer = RepeatingTimer(0.0416, self.on_timer)

        self._last_progress = 0

        self._context_menu = None
        self._current_set = None

    def load_set(self, set):
        self._current_set = set
        self._context_menu = ContextMenu(set, parent=self)

    def context_menu(self):
        return self._context_menu

    # listen for any spacebar touches for play/pause
    def eventFilter(self, obj, evt):
        if evt.type() == QEvent.KeyPress and obj.__class__ != QLineEdit and QApplication.activeModalWidget() is None:
            if evt.key() == Qt.Key_Space:
                self.toggle_play()
                return True
        return False

    def load(self, file_name):
        self._file_name = file_name

        self._highlighter.clear()

        try:
            self._capture = cv2.VideoCapture(self._file_name)
            if not self._capture.isOpened():
                raise Exception("Could not open file")
        except Exception as ex:
            getLogger('finprint').exception("Exception loading video {0}: {1}".format(self._file_name, ex))
            return False

        self.setFixedSize(VIDEO_WIDTH, VIDEO_HEIGHT)  # make this adjustable
        self._play_state = PlayState.Paused

        # don't start listening for spacebar until video is loaded and playable
        QCoreApplication.instance().installEventFilter(self)

        fps = self._capture.get(cv2.CAP_PROP_FPS)
        getLogger('finprint').debug("FPS {0}".format(fps))
        getLogger('finprint').debug("frame height {0}".format(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        getLogger('finprint').debug("frame width {0}".format(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)))
        getLogger('finprint').debug("widget height {0}".format(self.height()))
        getLogger('finprint').debug("widget width {0}".format(self.width()))


        # Take one frame to query height
        self.set_position(0)
        getLogger('finprint').debug("image height {0}".format(self._image.height()))
        getLogger('finprint').debug("image width {0}".format(self._image.width()))

        # Base line for measuring frame rate
        self.last_time = time.perf_counter()
        self._timer.interval = 1/fps #Set the timer to the frame rate of the video
        self._timer.start()
        return True

    def on_timer(self):
        t = time.perf_counter()
        pos = self.get_position()
        if self._play_state == PlayState.Playing:
            if pos - self._last_progress > PROGRESS_UPDATE_INTERVAL:
                self._last_progress = pos
                self.progressUpdate.emit(pos)
            self.load_frame()
        elif self._play_state == PlayState.SeekForward:
            pos += 360
            self._capture.set(cv2.CAP_PROP_POS_MSEC, pos)
            self.load_frame()
        elif self._play_state == PlayState.SeekBack:
            pos -= 360
            self._capture.set(cv2.CAP_PROP_POS_MSEC, pos)
            self.load_frame()

        self.update()

    def clear(self):
        self._timer.cancel()
        if self._capture is not None:
            self._capture.release()
        self._image = QImage(VIDEO_WIDTH, VIDEO_HEIGHT, QImage.Format_RGB888)
        self._image.fill(Qt.black)
        self.update()

    def _build_image(self, frame):
        t = time.perf_counter()
        image = None
        try:
            height, width, channels = frame.shape
            image = QImage(frame, width, height, QImage.Format_RGB888)
            image = image.scaledToWidth(VIDEO_WIDTH)
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

    def load_frame(self, current=False):
        t = time.perf_counter()
        diff = t - self.last_time
        self.last_time = t
        getLogger('finprint').debug("frame load diff {0:.4f}".format(diff))

        grabbed, frame = self._capture.retrieve() if current else self._capture.read()
        if grabbed:
            if diff < 0.06:  #skip frames if we start getting behind
                self._image = self._build_image(frame)
                self._onPositionChange(self.get_position())
            else:
                getLogger('finprint').debug('Skipping frame')

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

    def set_position(self, pos):
        self._capture.set(cv2.CAP_PROP_POS_MSEC, pos)
        self.load_frame(current=True)
        self._onPositionChange(self.get_position())

    def mousePressEvent(self, event):
        self.pause()
        self._highlighter.start_rect(event.pos())
        self.update()

    def mouseMoveEvent(self, event):
        if self.paused():
            self._dragging = True
            self._highlighter.set_rect(event.pos())
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
        self._play_state = PlayState.Playing
        self._highlighter.clear()
        self.playStateChanged.emit(self._play_state)

    def paused(self):
        return self._play_state == PlayState.Paused

    def get_position(self):
        return self._capture.get(cv2.CAP_PROP_POS_MSEC) if self._capture is not None else None

    def get_length(self):
        fps = self._capture.get(cv2.CAP_PROP_FPS)
        num_frames = self._capture.get(cv2.CAP_PROP_FRAME_COUNT)

        if fps == 0 or num_frames == 0:
            getLogger('finprint').exception("Failed to calculate length")
            return 0
        else:
            return (num_frames / fps) * 1000  # Returns milliseconds as a float

    def fast_forward(self):
        if self._play_state == PlayState.SeekForward:
            self.pause()
        else:
            self._play_state = PlayState.SeekForward
        self.playStateChanged.emit(self._play_state)

    def rewind(self):
        if self._play_state == PlayState.SeekBack:
            self.pause()
        else:
            self._play_state = PlayState.SeekBack
        self.playStateChanged.emit(self._play_state)

    def context_menu(self):
        if self._context_menu:
            self._context_menu.display()

    def step_back(self):
        self.pause()
        self.set_position(self.get_position() - FRAME_STEP)

    def step_forward(self):
        self.pause()
        self.set_position(self.get_position() + FRAME_STEP)

    def clear_extent(self):
        self._highlighter.clear()
