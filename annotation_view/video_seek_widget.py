from global_finprint import Animal, GlobalFinPrintServer
from video_player.cv_video_widget import VIDEO_WIDTH
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

        self.setMaximumWidth(VIDEO_WIDTH)

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

    def set_allowed_progress(self, progress):
        self.allowed_progress = progress

    def style(self):
        return """
            QSlider::groove:horizontal {
                background: rgb(126,211,33, 64);
                height: 2px;
                border-radius: 1px;
            }

            QSlider::sub-page:horizontal {
                background: qlineargradient(x1: 0, y1: 0,    x2: 0, y2: 1,
                    stop: 0 #33CC33, stop: 1 #99FF33);
                height: 2px;
            }

            QSlider::add-page:horizontal {
                background: rgb(126,211,33, 64);
                height: 2px;
            }

            QSlider::handle:horizontal {
                background: rgb(126,211,33);
                width: 13px;
                height: 13px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 6px;
            }

            QSlider::handle:horizontal:hover {
                background: rgb(0, 153, 0);
                width: 13px;
                height: 13px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 6px;
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
