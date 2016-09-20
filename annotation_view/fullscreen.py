from .util import convert_position
from .components import ClickLabel, SpeedButton, GenericButton
from .filter_widget import FilterWidget
from .video_seek_widget import VideoSeekWidget
from video_player import CvVideoWidget, PlayState
from global_finprint import GlobalFinPrintServer
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from logging import getLogger


class FullScreenLayout(QLayout):
    items = []
    hidden_controls = False
    hidden_offset = 0

    CONTROLS_HEIGHT = 125

    OFFSET_STEP = 10
    HIDDEN_OFFSET_MIN = 0
    HIDDEN_OFFSET_MAX = CONTROLS_HEIGHT

    def addItem(self, item):
        self.items.append(item)

    def setGeometry(self, rect):
        super().setGeometry(rect)

        screen = self.items[0]
        controls = self.items[1]

        availableHeight = rect.height()
        if self.hidden_offset < self.HIDDEN_OFFSET_MAX:
            availableHeight -= self.CONTROLS_HEIGHT

        screen.setGeometry(QRect(
            rect.x() + ((rect.width() - screen.widget()._target_width()) / 2),
            rect.y() + ((availableHeight - screen.widget()._target_height()) / 2),
            rect.width(),
            availableHeight
        ))

        controls.setGeometry(QRect(
            rect.x(),
            rect.height() - self.CONTROLS_HEIGHT + self.offset(),
            rect.width(),
            self.CONTROLS_HEIGHT
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

        # components
        self.video_player = CvVideoWidget(parent=self,
                                          onPositionChange=self.on_position_change,
                                          fullscreen=True)

        self.seek_bar = VideoSeekWidget(self.video_player)

        self.video_length_label = QLabel()
        self.video_length_label.setStyleSheet('color: #838C9E; font-size: 13px; padding-top: 10px;')

        self.filter_widget = FilterWidget()
        self.video_filter_button = ClickLabel()
        self.video_filter_button.setPixmap(QPixmap('images/filters.png'))

        self.fullscreen_button = ClickLabel()
        self.fullscreen_button.setPixmap(QPixmap('images/fullscreen-minimize.png'))

        self.set_label = QLabel(set.code)
        self.set_label.setStyleSheet('''
            color: #29566D;
            font-size: 13px;
            font-weight: bold;
            margin-right: 5px;
        ''')

        self.video_time_label = QLabel()
        self.video_time_label.setStyleSheet('color: #838C9E; font-size: 13px;')

        self.playback_speed_label = QLabel()
        self.playback_speed_label.setStyleSheet('color: #838C9E; font-size: 13px;')

        self.back15 = GenericButton()
        self.back15.setText('-15')

        self.back30 = GenericButton()
        self.back30.setText('-30')

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

        # layout
        controls_layout = QVBoxLayout()
        first_row = QHBoxLayout()
        first_row.addStretch(1)
        first_row.addWidget(self.video_filter_button)
        first_row.addWidget(self.fullscreen_button)
        controls_layout.addLayout(first_row)

        second_row = QHBoxLayout()
        second_row.addWidget(self.seek_bar)
        second_row.addWidget(self.video_length_label)
        controls_layout.addLayout(second_row)

        third_row = QHBoxLayout()
        third_row.addWidget(self.set_label)
        third_row.addWidget(self.video_time_label)
        third_row.addWidget(self.playback_speed_label)
        third_row.addSpacerItem(QSpacerItem(1, 1, QSizePolicy.Expanding))
        third_row.addWidget(self.back30)
        third_row.addWidget(self.back15)
        third_row.addWidget(self.step_back_button)
        third_row.addWidget(self.play_pause_button)
        third_row.addWidget(self.step_forward_button)
        third_row.addWidget(self.fast_forward_button)
        third_row.addSpacerItem(QSpacerItem(1, 1, QSizePolicy.Expanding))
        for button in self.speed_buttons:
            third_row.addWidget(button)
        controls_layout.addLayout(third_row)

        controls = QWidget()
        controls.setStyleSheet('background-color: white;')
        controls.setLayout(controls_layout)

        self.layout = FullScreenLayout()
        self.layout.addWidget(self.video_player)
        self.layout.addWidget(controls)
        self.setLayout(self.layout)

        # prepare video for display
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
        self.seek_bar.setMaximumWidth(self.frameGeometry().width())
        self.video_length_label.setText(convert_position(int(self.video_player.get_length())))
        self.playback_speed_label.setText('(0x)')
        self.wire_events()
        self.video_player.set_position(self.small_player.get_position())

    def wire_events(self):
        self.play_pause_button.clicked.connect(self.on_toggle_play)
        self.video_player.playStateChanged.connect(self.on_playstate_changed)
        self.video_player.playbackSpeedChanged.connect(self.on_playback_speed_changed)
        self.back15.clicked.connect(self.on_back15)
        self.back30.clicked.connect(self.on_back30)
        self.fast_forward_button.clicked.connect(self.on_fast_forward)
        self.step_back_button.clicked.connect(self.on_step_back)
        self.step_forward_button.clicked.connect(self.on_step_forward)
        self.video_filter_button.clicked.connect(self.on_video_filter_button)
        self.fullscreen_button.clicked.connect(self.on_fullscreen_toggle)
        self.seek_bar.tickSelected.connect(self.on_slider_tick)
        for button in self.speed_buttons:
            button.speedClick.connect(self.on_speed)
        QCoreApplication.instance().installEventFilter(self)

    def on_position_change(self, pos):
        self.video_time_label.setText(convert_position(int(pos)))
        self.seek_bar.setValue(int(pos))

    def on_playstate_changed(self, play_state):
        if play_state == PlayState.EndOfStream or play_state == PlayState.Paused:
            self.on_progress_update(self.video_player.get_position())  # update position on pause
            self.play_pause_button.setPixmap(self._play_pixmap)
        else:
            self.play_pause_button.setPixmap(self._pause_pixmap)

    def on_toggle_play(self):
        self.video_player.toggle_play()

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

    def on_speed(self, speed):
        self.video_player.set_speed(speed)

    def on_playback_speed_changed(self, speed):
        self.playback_speed_label.setText('({}x)'.format(int(speed) if int(speed) == speed else speed))

    def on_back15(self):
        self.video_player.jump_back(15)

    def on_back30(self):
        self.video_player.jump_back(30)

    def on_fullscreen_toggle(self):
        self.video_player.pause()
        self.filter_widget.hide()
        self.video_filter_button.setPixmap(QPixmap('images/filters.png'))
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

    def on_video_filter_button(self):
        img = self.filter_widget.toggle(self.video_filter_button)
        self.video_filter_button.setPixmap(QPixmap(img))
