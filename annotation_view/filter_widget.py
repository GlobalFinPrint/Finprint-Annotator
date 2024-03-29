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
        self._slider.setSingleStep(range_max)
        self._slider.setTickInterval(range_max)
        self._slider.setTickPosition(QSlider.TicksBelow)
        self._slider.setValue(range_min)
        self._slider.valueChanged.connect(self._on_value_change)
        self._slider.sliderPressed.connect(self._on_slider_pressed)
        self._slider.sliderReleased.connect(self._on_slider_released)
        self._slider_pressed = False

        range_labels = QWidget()
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

    def _on_slider_pressed(self):
        self._slider_pressed = True

    def _on_slider_released(self):
        self._slider_pressed = False
        self._on_value_change()

    def _on_value_change(self):
        if self._slider_pressed is False:
            self.change.emit()

    def value(self):
        return self._slider.value()


class ContrastToggle(QWidget):
    change = pyqtSignal()

    def __init__(self):
        super().__init__()

        contrast_label = QLabel('Contrast equalization')
        self.contrast_checkbox = QCheckBox()
        contrast_label.setBuddy(self.contrast_checkbox)
        self.contrast_checkbox.stateChanged.connect(self.on_state_changed)

        contrast_layout = QHBoxLayout()
        contrast_layout.addWidget(contrast_label)
        contrast_layout.addWidget(self.contrast_checkbox)
        self.setLayout(contrast_layout)

    def on_state_changed(self):
        self.change.emit()

    def checked(self):
        return self.contrast_checkbox.isChecked()


class FilterWidget(QWidget):
    change = pyqtSignal(int, int, bool)

    def __init__(self, video_filter_button):
        super().__init__()
        self.saturation_slider = FilterSlider('Saturation', 0, 100)
        self.brightness_slider = FilterSlider('Brightness', 0, 100)
        self._video_control_note = QLabel("Note: controls only applied to paused video")
        self.contrast_toggle = ContrastToggle()

        self.layout = QVBoxLayout()
        self.layout.addWidget(self._video_control_note)
        self.layout.addWidget(self.saturation_slider)
        self.layout.addWidget(self.brightness_slider)
        self.layout.addWidget(self.contrast_toggle)
        self.setLayout(self.layout)

        self.setStyleSheet('background-color: white;')
        self.setWindowFlags(Qt.CustomizeWindowHint)
        self.saturation_slider.change.connect(self.on_change)
        self.brightness_slider.change.connect(self.on_change)
        self.contrast_toggle.change.connect(self.on_change)
        self.offset = None
        self._video_filter_button = video_filter_button
        self.installEventFilter(self)


    def toggle(self, filter_button):
            if self.isVisible():
                self.hide()
                return False
            else:
                self.reveal(filter_button)
                return True

    def reveal(self, filter_button):
        # XXX make this widget align to the button container
        # top, as in some high resolution displays, the bottom of the
        # widget is off the screen
        xy = filter_button.parent().mapToGlobal(QPoint(
            filter_button.x()-30, filter_button.y() - 110
        ))
        self.setGeometry(xy.x() - 205, xy.y() - 105, 200, 100)
        self.show()

    def on_change(self):
        self.change.emit(self.saturation_slider.value(),
                         self.brightness_slider.value(),
                         self.contrast_toggle.checked())


    def mousePressEvent(self, event):
        # captures intial position of mouse press
        self.offset = event.pos()

    def eventFilter(self, source, evt):
        '''
        This EventFilter is installed only for filter widget event capture
        '''
        if evt.type() \
           and evt.type() == QEvent.MouseMove \
           and self.offset:
            new_pos_x = evt.globalX()
            new_pos_y = evt.globalY()
            old_pos_x = self.offset.x()
            old_pos_y = self.offset.y()
            self.move(new_pos_x - old_pos_x, new_pos_y - old_pos_y)
            # Stop bubbling
            return True
        elif evt.type() \
             and evt.type() == QEvent.WindowDeactivate:
            # avoid race condition between event filter installed in video layout widget
            # and full screen widget over the same object
            QTimer.singleShot(100, self.hide)
            # Stop bubbling
            return True
        else :
            return False


    def hide(self):
        '''
        Have to change color of button to darker one so overriding
        '''
        super(FilterWidget, self).hide()
        self._video_filter_button.setPixmap(QPixmap('images/filters.png'))
