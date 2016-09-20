from PyQt4.QtCore import *
from PyQt4.QtGui import *


class FilterWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.contrast_slider = QSlider()
        self.brightness_slider = QSlider()

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.contrast_slider)
        self.layout.addWidget(self.brightness_slider)

        self.setStyleSheet('background-color: white;')
        self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowStaysOnTopHint)

    def toggle(self, filter_button):
        if self.isVisible():
            self.hide()
        else:
            self.reveal(filter_button)

    def reveal(self, filter_button):
        xy = filter_button.parent().mapToGlobal(QPoint(
            filter_button.x(), filter_button.y()
        ))
        self.setGeometry(xy.x() - 205, xy.y() - 105, 200, 100)
        self.show()
