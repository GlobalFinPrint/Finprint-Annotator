import numpy as np
import cv2
import imutils
from threading import Thread
import time

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




class CvVideoWidget(QWidget):
    def __init__(self, parent=None, onPositionChange=None):
        QWidget.__init__(self, parent)

        self._paused = True
        self._dragging = False
        self._active = False
        self._highlight_corner1 = QPoint(0,0)
        self._highlight_corner2 = QPoint(0,0)
        self._onPositionChange = onPositionChange
        self._image = QBitmap(800, 600)

    def load(self, file_name):
        self._active = True
        self._file_name = file_name

        self._capture = cv2.VideoCapture(self._file_name)
        self.setMinimumSize(1024, 768)

        # Take one frame to query height
        grabbed, frame = self._capture.read()
        self._frame = None
        self._image = self._build_image(frame)

        self.last_time = time.perf_counter()

        self._capture_thread = Thread(target=self.thread_start, name="Capture Thread", daemon=True)
        self._capture_thread.start()

    def thread_start(self):
        while self._active:
            if not self._paused:
                self.query_frame()
            time.sleep(0.03)

    def clear(self):
        self._active = False
        self._capture.release()
        self._image = QBitmap(800, 600)
        self._image.fill(Qt.black)
        self.update()

    def _build_image(self, frame):
        frame = imutils.resize(frame, width=1200)
        height, width, channels = frame.shape
        if self._frame is None:
            self._frame = np.zeros((width, height, channels), np.uint8)
        self._frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return QImage(self._frame, width, height, QImage.Format_RGB888)

    def paintEvent(self, event):
        if self._active:
            painter = QPainter(self)
            painter.drawImage(QPoint(0, 0), self._image)
            if self._paused:
                painter.setPen(QPen(QBrush(Qt.green), 1, Qt.SolidLine))
                painter.drawRect(self.get_highlight())


    def on_timer(self):
        if not self._paused:
            self.query_frame()


    def query_frame(self):
        grabbed, frame = self._capture.read()
        if grabbed:
            #t = time.perf_counter()
            #print("{0:.4f}".format(t - self.last_time))
            #self.last_time = t
            # if self.f:
            #     hits = self._finder.check_frame(frame)
            #     if len(hits) > 0:
            #         print("Hit!")
            # f = not self.f

            self._image = self._build_image(frame)
            self.update()
            if self._onPositionChange is not None:
                self._onPositionChange(self.get_position())

    def get_highlight(self):
        return QRect(self._highlight_corner1.x(), self._highlight_corner1.y(), self._highlight_corner2.x() - self._highlight_corner1.x(), self._highlight_corner2.y() - self._highlight_corner1.y())

    def display_observation(self, pos, rect):
        self._highlight_corner1 = rect.topLeft()
        self._highlight_corner2 = rect.bottomRight()
        self._capture.set(cv2.CAP_PROP_POS_MSEC, pos)
        self.query_frame()
        self.repaint()

    def mousePressEvent(self, event):
        self._highlight_corner1 = event.pos()
        self._highlight_corner2 = event.pos()
        self.update()

    def mouseMoveEvent(self, event):
        self._dragging = True
        self._highlight_corner2 = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self.update()

    def pause(self):
        self._paused = True

    def play(self):
        self._paused = False

    def paused(self):
        return self._paused

    def get_position(self):
        return self._capture.get(cv2.CAP_PROP_POS_MSEC)

    def get_length(self):
        fps = self._capture.get(cv2.CAP_PROP_FPS)
        num_frames = self._capture.get(cv2.CAP_PROP_FRAME_COUNT)
        return num_frames / fps # Returns seconds as a float

    def fast_forward(self):
        self._capture.set(cv2.CAP_PROP_FPS, 120)

    def rewind(self):
        pass