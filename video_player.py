import numpy as np
from logging import getLogger
import cv2
import imutils
from threading import Thread
import time
from enum import Enum
from collections import deque

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from global_finprint import Extent

PROGRESS_UPDATE_INTERVAL = 30000


class Highlighter(object):
    def __init__(self):
        self._highlight_corner1 = QPoint(0, 0)
        self._highlight_corner2 = QPoint(0, 0)

    def get_rect(self):
        return QRect(self._highlight_corner1.x(), self._highlight_corner1.y(), self._highlight_corner2.x() - self._highlight_corner1.x(), self._highlight_corner2.y() - self._highlight_corner1.y())

    def start_rect(self, pos):
        self._highlight_corner1 = pos
        self._highlight_corner2 = pos

    def set_rect(self, pos):
        self._highlight_corner2 = pos

    def clear(self):
        self.start_rect(QPoint(0,0))

class PlayState(Enum):
    Playing = 1
    Paused = 2
    SeekBack = 3
    SeekForward = 4
    NotReady = 5
    EndOfStream = 6

## <<-went back to using a timer so this class isn't currently used-->>
## OpenCV isn't a true media player so we need to manage our own
##  frame rate.  The goal is the framerate we're trying to attain
class FrameRateAdjuster(object):
    def __init__(self, goal):
        self._max_values =  15
        self.goal = goal
        self._data = deque()
        self._last_result = goal

    ## We're returning the amount of time to sleep between
    ##   grabbing frames.
    def adjust(self):
        avg = 0
        for i in self._data:
            avg += i
        avg /= len(self._data)
        if avg > self.goal:
            self._last_result = self.goal - (avg - self.goal)
        else:
            self._last_result = self.goal + (self.goal - avg)
        return self._last_result

    ## The data we're collecting is the current amount
    ## of time between frame grabs.  We do an average of
    ## a series to smooth it out a bit
    def add(self, value):
        self._data.append(value)
        if len(self._data) < self._max_values:
            return self.goal

        self._data.popleft()
        return self.adjust()


class CvVideoWidget(QWidget):
    playStateChanged = pyqtSignal(PlayState)
    progressUpdate = pyqtSignal(int)

    def __init__(self, parent=None, onPositionChange=None):
        QWidget.__init__(self, parent)
        self._capture = None
        self._paused = True
        self._play_state = PlayState.NotReady
        self._frame = None

        self._dragging = False
        self._highlighter = Highlighter()
        self._onPositionChange = onPositionChange
        self.last_time = time.perf_counter()
        self._image = QBitmap(800, 600)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.on_timer)
        self._last_progress = 0

    # listen for any spacebar touches for play/pause
    def eventFilter(self, obj, evt):
        if evt.type() == QEvent.KeyPress and obj.__class__ != QLineEdit:
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

        self.setMinimumSize(800, 600)
        self._play_state = PlayState.Paused

        # don't start listening for spacebar until video is loaded and playable
        QCoreApplication.instance().installEventFilter(self)

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
        self._timer.start(33)
        return True

    def on_timer(self):
        pos = self.get_position()
        if self._play_state == PlayState.Playing:
            if pos - self._last_progress > PROGRESS_UPDATE_INTERVAL:
                self._last_progress = pos
                self.progressUpdate.emit(pos)
            self.load_frame()
        elif self._play_state == PlayState.SeekBack:
            pos -= 120
            self._capture.set(cv2.CAP_PROP_POS_MSEC, pos)
            self.load_frame()

        self.update()

    def clear(self):
        self._timer.stop()
        if self._capture is not None:
            self._capture.release()
        #self._image = QBitmap(800, 600)
        #self._image.fill(Qt.black)
        self.update()

    def _build_image(self, frame):
        try:
            frame = imutils.resize(frame, width=1024)
            height, width, channels = frame.shape
            if self._frame is None:
                self._frame = np.zeros((width, height, channels), np.uint8)

            self._frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except Exception as ex:
            getLogger('finprint').exception('Exception building image')

        return QImage(self._frame, width, height, QImage.Format_RGB888)

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.drawImage(QPoint(0, 0), self._image)
        if self._play_state == PlayState.Paused:
            painter.setPen(QPen(QBrush(Qt.green), 1, Qt.SolidLine))
            painter.drawRect(self._highlighter.get_rect())

    def load_frame(self):
        grabbed, frame = self._capture.read()
        if grabbed:
            t = time.perf_counter()
            diff = t - self.last_time
            self.last_time = t
            getLogger('finprint').debug("frame load diff {0:.4f}".format(diff))
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

    def display_observation(self, pos, extent):
        rect = extent.getRect(self._image.height(), self._image.width())
        self._highlighter.start_rect(rect.topLeft())
        self._highlighter.set_rect(rect.bottomRight())
        self.set_position(pos)
        self.repaint()

    def set_position(self, pos):
        self._capture.set(cv2.CAP_PROP_POS_MSEC, pos)
        getLogger('finprint').debug('Setting position to {0}'.format(pos))
        self.load_frame()
        self._onPositionChange(self.get_position())

    def mousePressEvent(self, event):
        if self.paused():
            self._highlighter.start_rect(event.pos())
            self.update()

    def mouseMoveEvent(self, event):
        if self.paused():
            self._dragging = True
            self._highlighter.set_rect(event.pos())
            self.update()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self.update()

    def toggle_play(self):
        if self._play_state == PlayState.Paused or self._play_state == PlayState.EndOfStream:
            self.play()
        else:
            self.pause()

    def pause(self):
        self._play_state = PlayState.Paused
        self.playStateChanged.emit(self._play_state)

    def play(self):
        if self._play_state == PlayState.EndOfStream:
            self.set_position(0)
        self._play_state = PlayState.Playing
        self._highlighter.clear()
        self.playStateChanged.emit(self._play_state)

    def paused(self):
        return self._play_state == PlayState.Paused

    def get_position(self):
        return self._capture.get(cv2.CAP_PROP_POS_MSEC)

    def get_length(self):
        fps = self._capture.get(cv2.CAP_PROP_FPS)
        num_frames = self._capture.get(cv2.CAP_PROP_FRAME_COUNT)

        if fps == 0 or num_frames == 0:
            getLogger('finprint').exception("Failed to calculate length")
            return 0
        else:
            return (num_frames / fps) * 1000 # Returns milliseconds as a float

    def fast_forward(self):
        self._capture.set(cv2.CAP_PROP_FPS, 120)

    def rewind(self):
        if self._play_state == PlayState.SeekBack:
            self.pause()
        else:
            self._play_state = PlayState.SeekBack
        self.playStateChanged.emit(self._play_state)
