import numpy as np
import cv2
import imutils
from threading import Thread
import time
from enum import Enum

from PyQt4.QtCore import *
from PyQt4.QtGui import *



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

class CvVideoWidget(QWidget):
    def __init__(self, parent=None, onPositionChange=None):
        QWidget.__init__(self, parent)
        self._capture = None
        self._paused = True
        self._play_state = PlayState.NotReady

        self._dragging = False
        self._active = False
        self._highlighter = Highlighter()
        self._onPositionChange = onPositionChange
        self._image = QBitmap(800, 600)

    def load(self, file_name):
        self._active = True
        self._play_state = PlayState.Paused
        self._file_name = file_name

        self._highlighter.clear()
        self._capture = cv2.VideoCapture(self._file_name)
        self.setMinimumSize(800, 600)

        # Take one frame to query height
        grabbed, frame = self._capture.read()
        self._frame = None
        self._image = self._build_image(frame)

        self.last_time = time.perf_counter()

        self._capture_thread = Thread(target=self.thread_start, name="Capture Thread", daemon=True)
        self._capture_thread.start()

    def thread_start(self):
        while self._active:
            #self.query_frame()
            self.update()
            time.sleep(0.03)

    def clear(self):
        self._active = False
        if self._capture is not None:
            self._capture.release()
        self._image = QBitmap(800, 600)
        self._image.fill(Qt.black)
        self.update()

    def _build_image(self, frame):
        frame = imutils.resize(frame, width=1024)
        height, width, channels = frame.shape
        if self._frame is None:
            self._frame = np.zeros((width, height, channels), np.uint8)
        self._frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return QImage(self._frame, width, height, QImage.Format_RGB888)

    def paintEvent(self, event):
        painter = QPainter(self)

        if self._play_state == PlayState.Playing:
            grabbed, frame = self._capture.read()
            if grabbed:
                #t = time.perf_counter()
                #print("{0:.4f}".format(t - self.last_time))
                #self.last_time = t
                self._image = self._build_image(frame)

        elif self._play_state == PlayState.SeekBack:
            pos = self.get_position()
            pos -= 120
            self._capture.set(cv2.CAP_PROP_POS_MSEC, pos)
            grabbed, frame = self._capture.read()
            if grabbed:
                self._image = self._build_image(frame)

        painter.drawImage(QPoint(0, 0), self._image)
        if self._play_state == PlayState.Paused:
            painter.setPen(QPen(QBrush(Qt.green), 1, Qt.SolidLine))
            painter.drawRect(self._highlighter.get_rect())
        else:
            self._onPositionChange(self.get_position())



    def get_highlight(self):
        return self._highlighter.get_rect()

    def display_observation(self, pos, rect):
        self._highlighter.start_rect(rect.topLeft())
        self._highlighter.set_rect(rect.bottomRight())
        self._capture.set(cv2.CAP_PROP_POS_MSEC, pos)
        #self.query_frame()
        self.repaint()

    def mousePressEvent(self, event):
        self._highlighter.start_rect(event.pos())
        self.update()

    def mouseMoveEvent(self, event):
        self._dragging = True
        self._highlighter.set_rect(event.pos())
        self.update()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self.update()

    def pause(self):
        self._play_state = PlayState.Paused

    def play(self):
        self._play_state = PlayState.Playing
        self._highlighter.clear()

    def paused(self):
        return self._play_state == PlayState.Paused

    def get_position(self):
        return self._capture.get(cv2.CAP_PROP_POS_MSEC)

    def get_length(self):
        fps = self._capture.get(cv2.CAP_PROP_FPS)
        num_frames = self._capture.get(cv2.CAP_PROP_FRAME_COUNT)
        return num_frames / fps # Returns seconds as a float

    def fast_forward(self):
        self._capture.set(cv2.CAP_PROP_FPS, 120)

    def rewind(self):
        self._play_state = PlayState.SeekBack