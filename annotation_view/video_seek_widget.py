from global_finprint import GlobalFinPrintServer, Observation
from video_player.cv_video_widget import VIDEO_WIDTH
from .util import convert_position
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class Tick(QLabel):
    clicked = pyqtSignal(int, Observation)
    tick_image = QImage('images/timeline-tick.png')

    def __init__(self, parent=None, position=0, obs=None):
        super().__init__(parent)
        self.position = position
        self.observation = obs
        self.setGeometry(QRect(0,0, Tick.tick_image.width(), Tick.tick_image.height()))
        self.setMouseTracking(True)
        self.setPixmap(QPixmap.fromImage(Tick.tick_image))

    def mousePressEvent(self, ev):
        self.clicked.emit(self.position, self.observation)

    def mouseMoveEvent(self, ev):
        QToolTip.showText(QCursor.pos(), convert_position(self.position))

class VideoSeekWidget(QSlider):
    tickSelected = pyqtSignal(int, Observation)

    def __init__(self, player):
        super(VideoSeekWidget, self).__init__()

        self.dragging = False
        self._player = player
        self._ticks = []
        self._set = None
        self._last_width = self.width()

        self.setOrientation(Qt.Horizontal)
        self.setStyleSheet(self.style())
        self.allowed_progress = 0
        self.setMaximumWidth(VIDEO_WIDTH)

    def resizeEvent(self, _):
        if self.width() != self._last_width:
            self._last_width = self.width()
            self.generate_ticks()

    def _posFromValue(self, val):
        return round(val * self.width() / self.maximum())

    def _valueFromPos(self, pos):
        return pos * self.maximum() / self.width()

    def load_set(self, set):
        self._set = set
        self.setMaximumWidth(self._player.width())
        self.generate_ticks()

    def clear_ticks(self):
        for t in self._ticks:
            t.setParent(None)
            t.deleteLater()
        self._ticks = []

    def generate_ticks(self):
        self.clear_ticks()
        if self._set:
            for obs in self._set.observations:
                x = self._posFromValue(obs.initial_time())
                tick = Tick(parent=self, position=obs.initial_time(), obs=obs)
                # There's a weird layout issue so I had to add a fudge factor to get the ticks to
                # be placed consistently with the slider
                x = round(x - (0.015 * x))
                tick.move(x, 0)
                tick.clicked.connect(self.tick_selected)
                self._ticks.append(tick)
                tick.show()
        self.update()

    def tick_selected(self, pos, obs):
        if not GlobalFinPrintServer().is_lead():
            if pos > self._set.progress:
                return
        self.setValue(pos)
        self.tickSelected.emit(pos, obs)

    def mousePressEvent(self, ev):
        """ Jump to click position """
        self.dragging = True
        #self.allowed_progress = max(self.value(), self.allowed_progress)
        self._player.pause()
        self.setValue(QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), ev.x(), self.width()))

    def mouseMoveEvent(self, ev):
        """ Jump to pointer position while moving """
        pos = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), ev.x(), self.width())
        x = self._posFromValue(pos)
        self.setValue(pos)
        QToolTip.showText(QCursor.pos(), convert_position(pos))

    def mouseReleaseEvent(self, ev):
        self.dragging = False
        self.set_position(self.value())

    def set_position(self, v):
        # do not allow fast forward for non-leads bob was here
        if GlobalFinPrintServer().is_lead():
            self._player.set_position(v)
        else:
            self._player.set_position(min(v, self._set.progress))

    def set_allowed_progress(self, progress):
        self.allowed_progress = progress

    def style(self):
        return """
            QSlider {
                padding-top: 10px;
            }

            QSlider::groove:horizontal {
                background: rgb(126,211,33, 64);
                height: 2px;
                border-radius: 1px;
            }

            QSlider::sub-page:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
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

