import numpy as np
import cv2
import sys
from math import floor

from PyQt4.QtCore import *
from PyQt4.QtGui import *


class VideoWidget(QWidget):
    def __init__(self, parent=None, onPositionChange=None):
        QWidget.__init__(self, parent)

        self._paused = True
        self._dragging = False
        self._highlight_corner1 = QPoint(0,0)
        self._highlight_corner2 = QPoint(0,0)
        self._onPositionChange = onPositionChange

        self._capture = cv2.VideoCapture("sharkcut.avi")
        # Take one frame to query height
        grabbed, frame = self._capture.read()
        height, width, channels = frame.shape
        self.setMinimumSize(1024, 768)
        #self.setMaximumSize(self.minimumSize())
        self._frame = None
        self._image = self._build_image(frame)
        # Paint every 50 ms
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.query_frame)
        self._timer.start(33)


    def _build_image(self, frame):
        height, width, channels = frame.shape
        if self._frame is None:
            self._frame = np.zeros((width, height, channels), np.uint8)
        self._frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return QImage(self._frame, width, height, QImage.Format_RGB888)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(QPoint(0, 0), self._image)
        if self._paused:
            painter.setPen(QPen(QBrush(Qt.green), 1, Qt.SolidLine))
            painter.drawRect(QRect(self._highlight_corner1.x(), self._highlight_corner1.y(), self._highlight_corner2.x() - self._highlight_corner1.x(), self._highlight_corner2.y() - self._highlight_corner1.y()))

    def query_frame(self):
        if not self._paused:
            grabbed, frame = self._capture.read()
            if grabbed:
                self._image = self._build_image(frame)
                self.update()
                if self._onPositionChange is not None:
                    self._onPositionChange(self._capture.get(cv2.CAP_PROP_POS_MSEC))

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

    def resume(self):
        self._paused = False

    def paused(self):
        return self._paused

    def get_position(self):
        return self._capture.get(cv2.CAP_PROP_POS_MSEC)

class VideoLayoutWidget(QWidget):
    def __init__(self):
        super(VideoLayoutWidget, self).__init__()

        # UI widgets
        self._video_player = VideoWidget(onPositionChange=self.on_position_change)
        self._pos_label = QLabel()
        self._pause_button = QPushButton('Resume')
        self._quit_button = QPushButton('Quit')
        self._observation_table = ObservationTable()

        # Buttons to record an observation of a registered species
        #  This will be dynamic based on each annotation session
        self._species_buttons = ['Grey Reef', 'Nurse']
        self._of_interest = QPushButton('Of Interest')

        self.setup_layout()
        self.wire_events()

    def wire_events(self):
        self._quit_button.clicked.connect(QCoreApplication.instance().quit)
        self._pause_button.clicked.connect(self.on_pause)

    def setup_layout(self):
        # Main container going top to bottom
        container = QVBoxLayout()
        container.setDirection(QBoxLayout.TopToBottom)

        # Main Video Window
        vid_box = QHBoxLayout()
        vid_box.addWidget(self._video_player)
        container.addLayout(vid_box)

        # Video control and observation register buttons
        vid_btn_box = QHBoxLayout()
        vid_btn_box.addStretch(1)
        vid_btn_box.addWidget(self._pos_label)
        vid_btn_box.addWidget(self._pause_button )

        # Video control and observation register buttons
        obs_btn_box = QHBoxLayout()
        obsbtn1 = QPushButton('Grey Reef')
        obsbtn1.clicked.connect(self.on_observation)

        obsbtn2 = QPushButton('Nurse')
        obsbtn2.clicked.connect(self.on_observation)

        obs_btn_box.addWidget(obsbtn1, alignment=Qt.AlignLeft)
        obs_btn_box.addWidget(obsbtn2, alignment=Qt.AlignLeft)

        btn_box = QHBoxLayout()
        btn_box.addLayout(obs_btn_box)
        btn_box.addLayout(vid_btn_box)

        container.addLayout(btn_box)

        # Observation table
        table_box = QHBoxLayout()
        table_box.addWidget(self._observation_table )
        container.addLayout(table_box)

        # App buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch(1)
        btn_box.addWidget(self._quit_button )
        container.addLayout(btn_box)

        self.setLayout(container)

    def on_pause(self):
        if self._video_player.paused():
            self._video_player.resume()
            self._pause_button.setText('Pause')
        else:
            self._video_player.pause()
            self._pause_button.setText('Resume')

    def on_observation(self, event):
        species = self.sender().text()
        pos = self._convert_position(self._video_player.get_position())
        self._observation_table.add_row(species, pos)

    def _convert_position(self, pos):
        s, m = divmod(floor(pos), 1000)
        h, s = divmod(s, 60)
        return "{0:02}:{1:02}:{2:03}".format(h, s, m)

    def on_position_change(self, pos):
        self._pos_label.setText(self._convert_position(pos))


class ObservationTable(QTableWidget):
    column_headers = ['Time', 'Species', 'Notes']
    def __init__(self, *args):
        super(ObservationTable, self).__init__(*args)
        self.set_data()
        self.show()

    def set_data(self):
        self.setColumnCount(len(ObservationTable.column_headers))
        self.setHorizontalHeaderLabels(ObservationTable.column_headers)

    def add_row(self, species, position):
        new_row_index = self.rowCount()
        self.setRowCount(new_row_index + 1)
        self.setItem(new_row_index, 0, QTableWidgetItem(position))
        self.setItem(new_row_index, 1, QTableWidgetItem(species))


if __name__ == '__main__':
    app = QApplication(sys.argv)

    widget = VideoWidget()
    widget.setWindowTitle('PyQt - OpenCV Test')
    widget.show()

    sys.exit(app.exec_())
