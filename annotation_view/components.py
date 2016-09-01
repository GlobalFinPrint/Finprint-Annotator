from PyQt4.QtCore import *
from PyQt4.QtGui import *


class ClickLabel(QLabel):
    clicked = pyqtSignal()

    def mouseReleaseEvent(self, ev):
        self.emit(SIGNAL('clicked()'))


class SpeedButton(QPushButton):
    def __init__(self, speed):
        super().__init__()
        self.speed = speed
        self.setText('{}x'.format(speed))
        self.setStyleSheet('''
            background-color: #29566D;
            color: white;
            border-radius: 4px;
            padding-top: 10px;
            padding-bottom: 10px;
            padding-left: 20px;
            padding-right: 20px;
            font-size: 14px;
        ''')
