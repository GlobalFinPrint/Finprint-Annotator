from PyQt4.QtCore import *
from PyQt4.QtGui import *


class FilterSlider(QWidget):
    change = pyqtSignal()

    def __init__(self, label, range_min, range_max):
        super().__init__()

        slider_label = QLabel(label)
        slider_label.setAlignment(Qt.AlignCenter)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(range_min, range_max)
        self._slider.setSingleStep(1)
        self._slider.setTickInterval(1)
        self._slider.setTickPosition(QSlider.TicksBelow)

        range_labels = QWidget()
        range_labels.setContentsMargins(0, 0, 0, 0)
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel(str(range_min)))
        range_layout.addStretch(1)
        range_layout.addWidget(QLabel(str(range_max)))
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_labels.setLayout(range_layout)

        layout = QVBoxLayout()
        layout.addWidget(slider_label)
        layout.addWidget(self._slider)
        layout.addWidget(range_labels)
        self.setLayout(layout)

        self._slider.valueChanged.connect(self._on_value_change)

    def _on_value_change(self):
        self.change.emit()

    def value(self):
        return self._slider.value()


class FilterWidget(QWidget):
    change = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.contrast_slider = FilterSlider('Contrast', -5, 5)
        self.brightness_slider = FilterSlider('Brightness', 0, 10)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.contrast_slider)
        self.layout.addWidget(self.brightness_slider)
        self.setLayout(self.layout)

        self.setStyleSheet('background-color: white;')
        self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowStaysOnTopHint)

        self.contrast_slider.change.connect(self.on_change)

    def toggle(self, filter_button):
        if self.isVisible():
            self.hide()
            return 'images/filters.png'
        else:
            self.reveal(filter_button)
            return 'images/filters-active.png'

    def reveal(self, filter_button):
        xy = filter_button.parent().mapToGlobal(QPoint(
            filter_button.x(), filter_button.y()
        ))
        self.setGeometry(xy.x() - 205, xy.y() - 105, 200, 100)
        self.show()

    def on_change(self):
        self.change.emit(self.contrast_slider.value(), self.brightness_slider.value())
