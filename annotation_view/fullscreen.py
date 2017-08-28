from .util import convert_position
from .key_press_handler import MultiKeyPressHandler
from .components import ClickLabel, SpeedButton, GenericButton
from .filter_widget import FilterWidget
from .video_seek_widget import VideoSeekWidget
from video_player import VlcVideoWidget, PlayState
from global_finprint import GlobalFinPrintServer
from PyQt4.QtGui import *
from PyQt4.QtCore import *



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

        # vlc will maintain the video aspect for a given size container, so no
        # need to center the video frame in the container
        screen.setGeometry(QRect(
            rect.x(),
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
        return self.parent().frameGeometry().size()

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
    FRAME_STEP = 70  # milli seconds
    keyPressed = pyqtSignal(QEvent)

    def __init__(self, set, video_file, small_player):
        super().__init__()
        self.showFullScreen()

        self.setStyleSheet('background-color: black;')
        self.current_set = set
        self.small_player = small_player
        # components
        self.fullscreen_video_player = VlcVideoWidget(parent=self,
                                                      onPositionChange=self.on_position_change,
                                                      fullscreen=True)

        self.seek_bar = VideoSeekWidget(self.fullscreen_video_player)

        self.video_length_label = QLabel()
        self.video_length_label.setStyleSheet('color: #838C9E; font-size: 13px; padding-top: 10px;')

        self.video_filter_button = ClickLabel()
        self.video_filter_button.setPixmap(QPixmap('images/filters.png'))
        self.filter_widget = FilterWidget(self.video_filter_button)


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

        self.back15 = ClickLabel()
        self.back15.setPixmap(QPixmap('images/jump_back-15s.png'))
        # adding hover text
        self.back15.setToolTip("15 second rewind (<Control> + Down Arrow)")

        self.back05 = ClickLabel()
        self.back05.setPixmap(QPixmap('images/jump_back-5s.png'))
        # adding hover text
        self.back05.setToolTip("5 second rewind (<Control> + Left Arrow)")

        self.step_back_button = ClickLabel()
        self.step_back_button.setPixmap(QPixmap('images/video_control-step_back.png'))
        # adding hover text
        self.step_back_button.setToolTip("Back one frame (<Shift> + Left Arrow)")

        self._play_pixmap = QPixmap('images/video_control-play.png')
        self._pause_pixmap = QPixmap('images/video_control-pause.png')
        self.play_pause_button = ClickLabel()
        self.play_pause_button.setPixmap(self._play_pixmap)

        self.step_forward_button = ClickLabel()
        self.step_forward_button.setPixmap(QPixmap('images/video_control-step_forward.png'))
        # adding hover text
        self.step_forward_button.setToolTip("Forward one frame (<Shift> + Right Arrow)")

        self.fast_forward_button = ClickLabel()
        self.fast_forward_button.setPixmap(QPixmap('images/video_control-fast_forward.png'))
        if not GlobalFinPrintServer().is_lead():
            self.fast_forward_button.setVisible(False)
        self.speed_buttons = list(SpeedButton(speed) for speed in [0.5, 1.5, 3])

        # Initialize/Sync full screen timer with incoming small player timer
        self.fullscreen_video_player.timer_vo.timer_duration_ms = self.small_player.get_position()

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
        third_row.addWidget(self.back15)
        third_row.addWidget(self.back05)
        third_row.addWidget(self.step_back_button)
        third_row.addWidget(self.play_pause_button)
        third_row.addWidget(self.step_forward_button)
        third_row.addWidget(self.fast_forward_button)
        third_row.addSpacerItem(QSpacerItem(1, 1, QSizePolicy.Expanding))
        for button in self.speed_buttons:
            third_row.addWidget(button)
            if not GlobalFinPrintServer().is_lead() and button.speed > 1.5:
                button.setVisible(False)
        controls_layout.addLayout(third_row)

        controls = QWidget()
        controls.setStyleSheet('background-color: white;')
        controls.setLayout(controls_layout)

        self.layout = FullScreenLayout()
        self.layout.addWidget(self.fullscreen_video_player)
        self.layout.addWidget(controls)
        self.setLayout(self.layout)

        # prepare video for display
        self.prepare(video_file, True)

        # wire events for interactivity
        self.wire_events()

        # installing eventFilter for controlling sat/brightness popup hide and show
        self.filter_widget.installEventFilter(self)
        self.video_filter_button.installEventFilter(self)

    def revive(self, set, video_file, small_player):
        set_changed = self.current_set != set
        self.current_set = set
        self.small_player = small_player

        # Initialize/Sync full screen timer with incoming small player timer
        self.fullscreen_video_player.timer_vo.timer_duration_ms = self.small_player.get_position()

        self.prepare(video_file, set_changed)
        self.show()

    def prepare(self, video_file, set_changed=False):
        self.fullscreen_video_player.clear_extent()
        if set_changed:
            self.fullscreen_video_player.load_set(self.current_set)
            self.fullscreen_video_player.load(video_file)
            self.seek_bar.load_set(self.current_set)
            self.seek_bar.setMaximum(int(self.fullscreen_video_player.get_length()))
            self.seek_bar.set_allowed_progress(self.current_set.progress)
            self.seek_bar.setMaximumWidth(self.frameGeometry().width())
        else:
            self.seek_bar.generate_ticks()
        self.seek_bar.set_allowed_progress(self.current_set.progress)
        self.video_length_label.setText(convert_position(int(self.fullscreen_video_player.get_length())))
        self.playback_speed_label.setText('(0x)')
        #intializing TimerVO with present time
        self.fullscreen_video_player.set_position(self.small_player.get_position())
        self.filter_widget.installEventFilter(self)
        self.video_filter_button.installEventFilter(self)
        QCoreApplication.instance().installEventFilter(self.fullscreen_video_player)

    def wire_events(self):
        self.play_pause_button.clicked.connect(self.on_toggle_play)
        self.fullscreen_video_player.playStateChanged.connect(self.on_playstate_changed)
        self.fullscreen_video_player.playbackSpeedChanged.connect(self.on_playback_speed_changed)
        self.filter_widget.change.connect(self.on_filter_change)
        self.back15.clicked.connect(self.on_back15)
        self.back05.clicked.connect(self.on_back05)
        self.fast_forward_button.clicked.connect(self.on_fast_forward)
        self.step_back_button.clicked.connect(self.on_step_back)
        self.step_forward_button.clicked.connect(self.on_step_forward)
        self.fullscreen_button.clicked.connect(self.on_fullscreen_toggle)
        self.seek_bar.tickSelected.connect(self.on_slider_tick)
        for button in self.speed_buttons:
            button.speedClick.connect(self.on_speed)

        self.keyPressed.connect(self.on_key)
        # multi key press event handling set
        self.keylist = set()
        self.firstrelease = False

    def on_position_change(self, pos):
        self.video_time_label.setText(convert_position(int(pos)))
        self.seek_bar.setValue(int(pos))

    def on_playstate_changed(self, play_state):
        if play_state == PlayState.EndOfStream or play_state == PlayState.Paused:
            self.on_progress_update(self.fullscreen_video_player.get_position())  # update position on pause
            self.play_pause_button.setPixmap(self._play_pixmap)
        else:
            self.play_pause_button.setPixmap(self._pause_pixmap)

    def on_toggle_play(self):
        self.fullscreen_video_player.toggle_play()

    def on_progress_update(self, progress):
        if self.current_set is not None:
            self.current_set.update_progress(progress)

    def on_rewind(self):
        self.fullscreen_video_player.rewind()

    def on_fast_forward(self):
        self.fullscreen_video_player.fast_forward()

    def on_step_back(self):
        self.fullscreen_video_player.scrub_position(self.fullscreen_video_player.get_position() - self.FRAME_STEP)

    def on_step_forward(self):
        self.fullscreen_video_player.scrub_position(self.fullscreen_video_player.get_position() + self.FRAME_STEP)

    def on_speed(self, speed):
        self.fullscreen_video_player.set_speed(speed)

    def on_playback_speed_changed(self, speed):
        self.playback_speed_label.setText('({}x)'.format(int(speed) if int(speed) == speed else speed))

    ''' Pause the video and Go back 15 seconds '''
    def on_back15(self):
        self.fullscreen_video_player.scrub_position(self.fullscreen_video_player.get_position() - 15000)

    ''' Pause the video and Go back 5 seconds '''
    def on_back05(self):
        self.fullscreen_video_player.scrub_position(self.fullscreen_video_player.get_position() - 5000)


    def on_fullscreen_toggle(self):
        self.fullscreen_video_player.pause()
        self.filter_widget.hide()
        self.video_filter_button.setPixmap(QPixmap('images/filters.png'))
        #setting scrub postion with new changed position of normal screen where it paused
        self.small_player.scrub_position(self.fullscreen_video_player.get_position())
        self.small_player.parent()._observation_table.refresh_model()
        self.filter_widget.removeEventFilter(self)
        self.video_filter_button.removeEventFilter(self)
        QCoreApplication.instance().installEventFilter(self.small_player)
        self.hide()
        self.fullscreen_video_player.clear()
        self.small_player.parent().is_fullscreen = False

    def on_slider_tick(self, _, obs):
        evt = sorted(obs.events, key=lambda e: e.create_datetime)[0]
        self.fullscreen_video_player.pause()
        self.fullscreen_video_player.display_event(evt.event_time, evt.extent)

    def refresh_seek_bar(self):
        self.seek_bar.load_set(self.current_set)

    def eventFilter(self, source, evt):
        '''
        This EventFilter is installed only for filter widget/ video filter button event capture
        '''
        if source is self.filter_widget:
            if evt.type() == QEvent.KeyPress and QApplication.activeModalWidget() is None:
                # handles keyboard shortcut
                self.keyboard_shortcut_event(evt)
                # Stop bubbling
                return True
        elif source is self.video_filter_button and evt.type() == QEvent.MouseButtonPress:
            filter_widget_visible = self.filter_widget.toggle(self.video_filter_button)
            if filter_widget_visible:
                self.video_filter_button.setPixmap(QPixmap('images/filters-active.png'))
            else:
                self.video_filter_button.setPixmap(QPixmap('images/filters.png'))
            # Stop bubbling
            return True

        # bubble up
        return False

    def mousePressEvent(self, mouse_evt):
        print("fullscreen > mousePressEvent")
        self.setFocus()
        if self.filter_widget.isVisible():
            self.filter_widget.hide()
            self.video_filter_button.setPixmap(QPixmap('images/filters.png'))


    def on_filter_change(self, saturation, brightness, contrast):
        self.fullscreen_video_player.saturation = saturation
        self.fullscreen_video_player.brightness = brightness
        self.fullscreen_video_player.contrast = contrast
        if self.fullscreen_video_player.is_paused():
            self.fullscreen_video_player.refresh_frame()


    def keyPressEvent(self, event):
        '''
        overriding system keyReleaseEvent ,
        adds keyEvent in keyList when later key is
        released in case of multi key press
        '''
        super(FullScreen, self).keyPressEvent(event)
        if event.key() == Qt.Key_Escape:
            self.on_fullscreen_toggle()
        elif event.key() == Qt.Key_T:
            self.layout.hidden_controls = not self.layout.hidden_controls
            self.layout.update()
        else :
            self.firstrelease = True
            self.keylist.add(event.key())
            self.keyPressed.emit(event)

    def on_key(self, event):
        if event.key() == Qt.Key_F5:
            self.on_fullscreen_toggle()


    def keyReleaseEvent(self, evt):
        '''
        overriding system keyReleaseEvent ,
        adds keyEvent in keyList when later key is
        released in case of multi key press
        '''
        super(FullScreen, self).keyReleaseEvent(evt)
        if self.firstrelease == True:
            self.keylist.add(evt.key())
            MultiKeyPressHandler().process_multi_key_press(self)

        self.firstrelease = False
        if self.keylist :
            self.keylist.pop()

    def keyboard_shortcut_event(self, evt):
        '''
        Considering that keyboard shortcut in windows
        as per explained is anything which involves shift modifier
        or control modifier or both or F1.
        '''
        if self.filter_widget.isVisible() :
            MultiKeyPressHandler().handle_keyboard_shortcut_event(evt, self.filter_widget)
            self.video_filter_button.setPixmap(QPixmap('images/filters.png'))
