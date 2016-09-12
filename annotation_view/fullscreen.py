from .util import convert_position
from .components import ClickLabel, SpeedButton
from .video_seek_widget import VideoSeekWidget
from video_player import CvVideoWidget, PlayState
from global_finprint import GlobalFinPrintServer
from PyQt4.QtGui import *
from PyQt4.QtCore import *


class FullScreenLayout(QLayout):
    items = []
    hidden_controls = False
    hidden_offset = 0

    SEEK_HEIGHT = 45
    SPACING = 5
    CONTROL_HEIGHT = 50

    OFFSET_STEP = 10
    HIDDEN_OFFSET_MIN = 0
    HIDDEN_OFFSET_MAX = SEEK_HEIGHT + SPACING + CONTROL_HEIGHT

    def addItem(self, item):
        self.items.append(item)

    def setGeometry(self, rect):
        super().setGeometry(rect)

        screen = self.items[0]
        seek_bar = self.items[1]
        controls = self.items[2]

        screen.setGeometry(QRect(
            rect.x(),
            rect.y(),
            rect.width(),
            screen.geometry().height()
        ))

        seek_bar.setGeometry(QRect(
            rect.x(),
            rect.height() - self.SEEK_HEIGHT - self.CONTROL_HEIGHT - self.SPACING + self.offset(),
            rect.width(),
            self.SEEK_HEIGHT
        ))

        controls.setGeometry(QRect(
            rect.x(),
            rect.height() - self.CONTROL_HEIGHT + self.offset(),
            rect.width(),
            self.CONTROL_HEIGHT
        ))

    def sizeHint(self):
        return self.parent().frameGeometry()

    def count(self):
        return len(self.items)

    def itemAt(self, idx):
        return self.items[idx] if 0 <= idx < len(self.items) else None

    def takeAt(self, idx):
        item = self.items[idx]
        del self.items[idx]
        return item

    def offset(self):
        if self.hidden_controls:
            self.hidden_offset = min(self.hidden_offset + self.OFFSET_STEP, self.HIDDEN_OFFSET_MAX)
        else:
            self.hidden_offset = max(self.hidden_offset - self.OFFSET_STEP, self.HIDDEN_OFFSET_MIN)

        if self.hidden_offset not in (self.HIDDEN_OFFSET_MIN, self.HIDDEN_OFFSET_MAX):
            self.update()

        return self.hidden_offset


class FullScreen(QWidget):
    def __init__(self, set, video_file, small_player):
        super().__init__()
        self.showFullScreen()

        self.setStyleSheet('background-color: black;')
        self.current_set = set
        self.small_player = small_player

        self.layout = FullScreenLayout()
        self.video_player = CvVideoWidget(parent=self,
                                          onPositionChange=self.on_position_change,
                                          fullscreen=True)

        self.seek_bar = VideoSeekWidget(self.video_player)

        self.video_length_label = QLabel()
        self.video_length_label.setStyleSheet('color: #838C9E; font-size: 13px; padding-top: 10px;')

        seek_bar_holder = QWidget()
        seek_bar_holder.setStyleSheet('background-color: white;')
        seek_bar_holder_layout = QHBoxLayout()
        seek_bar_holder_layout.addWidget(self.seek_bar)
        seek_bar_holder_layout.addWidget(self.video_length_label)
        seek_bar_holder.setLayout(seek_bar_holder_layout)

        controls_holder = QWidget()
        controls_holder.setStyleSheet('background-color: white;')
        controls_holder_layout = QHBoxLayout()
        controls_holder_layout.setAlignment(Qt.AlignLeft)

        self.set_label = QLabel(set.code)
        self.set_label.setStyleSheet('''
            color: #29566D;
            font-size: 13px;
            font-weight: bold;
            margin-right: 5px;
        ''')

        self.video_time_label = QLabel()
        self.video_time_label.setStyleSheet('color: #838C9E; font-size: 13px;')

        self.rewind_button = ClickLabel()
        self.rewind_button.setPixmap(QPixmap('images/video_control-rewind.png'))

        self.step_back_button = ClickLabel()
        self.step_back_button.setPixmap(QPixmap('images/video_control-step_back.png'))

        self._play_pixmap = QPixmap('images/video_control-play.png')
        self._pause_pixmap = QPixmap('images/video_control-pause.png')
        self.play_pause_button = ClickLabel()
        self.play_pause_button.setPixmap(self._play_pixmap)

        self.step_forward_button = ClickLabel()
        self.step_forward_button.setPixmap(QPixmap('images/video_control-step_forward.png'))

        self.fast_forward_button = ClickLabel()
        self.fast_forward_button.setPixmap(QPixmap('images/video_control-fast_forward.png'))
        if not GlobalFinPrintServer().is_lead():
            self.fast_forward_button.setVisible(False)

        self.speed_buttons = list(SpeedButton(speed) for speed in [0.5, 1.5, 3])

        self.fullscreen_button = ClickLabel()
        self.fullscreen_button.setPixmap(QPixmap('images/fullscreen-minimize.png'))

        controls_holder_layout.addWidget(self.set_label)
        controls_holder_layout.addWidget(self.video_time_label)
        controls_holder_layout.addSpacerItem(QSpacerItem(1, 1, QSizePolicy.Expanding))
        controls_holder_layout.addWidget(self.rewind_button)
        controls_holder_layout.addWidget(self.step_back_button)
        controls_holder_layout.addWidget(self.play_pause_button)
        controls_holder_layout.addWidget(self.step_forward_button)
        controls_holder_layout.addWidget(self.fast_forward_button)
        for button in self.speed_buttons:
            controls_holder_layout.addWidget(button)
        controls_holder_layout.addWidget(self.fullscreen_button)

        controls_holder.setLayout(controls_holder_layout)

        self.layout.addWidget(self.video_player)
        self.layout.addWidget(seek_bar_holder)
        self.layout.addWidget(controls_holder)
        self.setLayout(self.layout)

        self.prepare(video_file)

    def revive(self, set, video_file, small_player):
        # TODO fix frame rate on revived fullscreen view
        self.current_set = set
        self.small_player = small_player
        self.prepare(video_file)
        self.show()

    def prepare(self, video_file):
        self.video_player.load_set(self.current_set)
        self.video_player.load(video_file)
        self.seek_bar.load_set(self.current_set)
        self.seek_bar.setMaximum(int(self.video_player.get_length()))
        self.seek_bar.set_allowed_progress(self.current_set.progress)
        self.video_length_label.setText(convert_position(int(self.video_player.get_length())))
        self.wire_events()
        self.video_player.set_position(self.small_player.get_position())

    def wire_events(self):
        self.video_player.playStateChanged.connect(self.on_playstate_changed)
        self.rewind_button.clicked.connect(self.on_rewind)
        self.fast_forward_button.clicked.connect(self.on_fast_forward)
        self.step_back_button.clicked.connect(self.on_step_back)
        self.step_forward_button.clicked.connect(self.on_step_forward)
        self.fullscreen_button.clicked.connect(self.on_fullscreen_toggle)
        self.seek_bar.tickSelected.connect(self.on_slider_tick)
        for button in self.speed_buttons:
            pass  # TODO hook up buttons
        QCoreApplication.instance().installEventFilter(self)

    def on_position_change(self, pos):
        self.video_time_label.setText(convert_position(int(pos)))
        self.seek_bar.setValue(int(pos))

    def on_playstate_changed(self, play_state):
        if play_state == PlayState.EndOfStream or play_state == PlayState.Paused:
            self.on_progress_update(self.video_player.get_position())  # update position on pause
            self.play_pause_button.setPixmap(self._play_pixmap)
            self.layout.hidden_controls = False
        else:
            self.play_pause_button.setPixmap(self._pause_pixmap)
            self.layout.hidden_controls = True

    def on_progress_update(self, progress):
        if self.current_set is not None:
            self.current_set.update_progress(progress)

    def on_rewind(self):
        self.video_player.rewind()

    def on_fast_forward(self):
        self.video_player.fast_forward()

    def on_step_back(self):
        self.video_player.step_back()

    def on_step_forward(self):
        self.video_player.step_forward()

    def on_fullscreen_toggle(self):
        self.video_player.pause()
        self.small_player.set_position(self.video_player.get_position())
        self.small_player.parent()._observation_table.refresh_model()
        QCoreApplication.instance().removeEventFilter(self)
        QCoreApplication.instance().installEventFilter(self.small_player)
        self.hide()
        self.small_player.parent().is_fullscreen = False

    def on_slider_tick(self, _, obs):
        evt = sorted(obs.events, key=lambda e: e.event_time)[0]
        self.video_player.pause()
        self.video_player.display_event(evt.event_time, evt.extent)

    def refresh_seek_bar(self):
        self.seek_bar.load_set(self.current_set)

    def eventFilter(self, obj, evt):
        if evt.type() == QEvent.KeyPress and evt.key() == Qt.Key_Escape:
            self.on_fullscreen_toggle()
            return True
        elif evt.type() == QEvent.KeyPress and evt.key() == Qt.Key_T:
            self.layout.hidden_controls = not self.layout.hidden_controls
            self.layout.update()
            return True
        return False
