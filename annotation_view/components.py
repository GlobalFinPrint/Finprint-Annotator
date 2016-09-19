from PyQt4.QtCore import *
from PyQt4.QtGui import *


class ClickLabel(QLabel):
    clicked = pyqtSignal()

    def mouseReleaseEvent(self, ev):
        self.emit(SIGNAL('clicked()'))


class GenericButton(QPushButton):
    def __init__(self):
        super().__init__()
        self.setStyleSheet('''
            background-color: #29566D;
            color: white;
            border-radius: 4px;
            padding-top: 10px;
            padding-bottom: 10px;
            padding-left: 15px;
            padding-right: 15px;
            font-size: 12px;
        ''')


class SpeedButton(GenericButton):
    speedClick = pyqtSignal(float)

    def __init__(self, speed):
        super().__init__()
        self.speed = speed
        self.setText('{}x'.format(speed))

    def mouseReleaseEvent(self, _):
        self.speedClick.emit(self.speed)
