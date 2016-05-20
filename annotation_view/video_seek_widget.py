from global_finprint import Animal, GlobalFinPrintServer
from .util import convert_position
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class VideoSeekWidget(QSlider):
    item_select = pyqtSignal(Animal)

    def __init__(self, player):
        super(VideoSeekWidget, self).__init__()

        self.dragging = False
        self._player = player
        self.setOrientation(Qt.Horizontal)
        self.setStyleSheet(self.style())
        self.allowed_progress = None

        self.sliderPressed.connect(self._pressed)
        self.sliderMoved.connect(self._moved)
        self.sliderReleased.connect(self._released)

    def _pressed(self):
        self.dragging = True
        self.allowed_progress = max(self.value(), self.allowed_progress)
        self._player.pause()

    def _moved(self, pos):
        QToolTip.showText(QCursor.pos(), convert_position(pos))

    def _released(self):
        self.dragging = False
        # do not allow fast forward for non-leads
        if GlobalFinPrintServer().is_lead() or self.allowed_progress is None:
            self._player.set_position(self.value())
        else:
            self._player.set_position(min(self.value(), self.allowed_progress))

    def setMaximum(self, value):
        super(VideoSeekWidget, self).setMaximum(value)

    def set_allowed_progress(self, progress):
        self.allowed_progress = progress

    def style(self):
        return """
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 10px;
                border-radius: 4px;
            }

            QSlider::sub-page:horizontal {
                background: qlineargradient(x1: 0, y1: 0,    x2: 0, y2: 1,
                    stop: 0 #66e, stop: 1 #bbf);
                background: qlineargradient(x1: 0, y1: 0.2, x2: 1, y2: 1,
                    stop: 0 #bbf, stop: 1 #55f);
                border: 1px solid #777;
                height: 10px;
                border-radius: 4px;
            }

            QSlider::add-page:horizontal {
                background: #fff;
                border: 1px solid #777;
                height: 10px;
                border-radius: 4px;
            }

            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #eee, stop:1 #ccc);
                border: 1px solid #777;
                width: 13px;
                margin-top: -2px;
                margin-bottom: -2px;
                border-radius: 4px;
            }

            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #fff, stop:1 #ddd);
                border: 1px solid #444;
                border-radius: 4px;
            }

            QSlider::sub-page:horizontal:disabled {
                background: #bbb;
                border-color: #999;
            }

            QSlider::add-page:horizontal:disabled {
                background: #eee;
                border-color: #999;
            }

            QSlider::handle:horizontal:disabled {
                background: #eee;
                border: 1px solid #aaa;
                border-radius: 4px;
            }
            """
