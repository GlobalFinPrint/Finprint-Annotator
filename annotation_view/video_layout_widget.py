import os
from logging import getLogger
from video_player import VlcVideoWidget, PlayState, TimerVO
from global_finprint import GlobalFinPrintServer
from config import global_config
from .video_seek_widget import VideoSeekWidget
from .filter_widget import FilterWidget
from .fullscreen import FullScreen
from .components import ClickLabel, SpeedButton, GenericButton
from .observation_table import ObservationTable
from .util import convert_position
from .key_press_handler import MultiKeyPressHandler
from PyQt4.QtCore import *
from PyQt4.QtGui import *



#taking id of both attribute as constant in all database
MARK_90_MIN_GLOBAL_ID = 24
MARK_HAUL_TIME_GLOBAL_ID = 23


class VideoLayoutWidget(QWidget):
    fullscreen = None
    is_fullscreen = False
    FRAME_STEP = 70  # milli seconds
    keyPressed = pyqtSignal(QEvent)

    def __init__(self, main_window):
        super(VideoLayoutWidget, self).__init__()

        self._main_window = main_window

        button_style = """QPushButton { background: rgb(41, 86, 109);
                                        color:white;
                                        font: 12pt "Arial";
                                        border-radius: 4px;
                                        margin-left: 25px;
                                        padding-top: 4px;
                                        padding-bottom: 4px;
                                        padding-left: 5px;s
                                        padding-right: 5px; }
                                       QPushButton:hover { background: rgb(41, 86, 109, 128); }
                                       QPushButton:disabled { background: rgb(131,140,158, 128);
                                                              color:white; }"""

        # UI widgets
        self.vid_box = None
        self._video_label = QLabel('')
        self._video_label.setStyleSheet("""color:rgb(74,74,74); font: 75 12pt "Arial";""")
        self._video_player = VlcVideoWidget(parent=self, onPositionChange=self.on_position_change)
        self._pos_label = QLabel()
        self._duration_label = QLabel()
        self._playback_speed_label = QLabel()
        self._data_loading = False

        self._play_pixmap = QPixmap('images/video_control-play.png')
        self._pause_pixmap = QPixmap('images/video_control-pause.png')

        self._slider = VideoSeekWidget(self._video_player)
        self._slider.hide()

        self._rew_button = ClickLabel()
        self._rew_button.setPixmap(QPixmap('images/video_control-rewind.png'))

        self._back15 = ClickLabel()
        self._back15.setPixmap(QPixmap('images/jump_back-15s.png'))
        self._back15.setToolTip("15 second rewind (<Control> + Down Arrow)")

        self._back05 = ClickLabel()
        self._back05.setPixmap(QPixmap('images/jump_back-5s.png'))
        # adding hover text
        self._back05.setToolTip("5 second rewind (<Control> + Left Arrow)")

        self._ff_button = ClickLabel()
        self._ff_button.setPixmap(QPixmap('images/video_control-fast_forward.png'))
        self._ff_button.setVisible(False)

        self._step_back_button = ClickLabel()
        self._step_back_button.setPixmap(QPixmap('images/video_control-step_back.png'))
        # adding hover text
        self._step_back_button.setToolTip("Back one frame (<Shift> + Left Arrow)")

        self._toggle_play_button = ClickLabel()
        self._toggle_play_button.setPixmap(self._play_pixmap)

        self._step_forward_button = ClickLabel()
        self._step_forward_button.setPixmap(QPixmap('images/video_control-step_forward.png'))
        #adding hover text
        self._step_forward_button.setToolTip("Forward one frame (<Shift> + Right Arrow)")

        self._filter_widget = FilterWidget()
        self._video_filter_label = QLabel("Note: controls only applied to paused video")
        self._video_filter_button = ClickLabel()
        self._video_filter_button.setPixmap(QPixmap('images/filters.png'))
        self._video_filter_button.setToolTip("Note: controls only applied to paused video")

        self._fullscreen_button = ClickLabel()
        self._fullscreen_button.setPixmap(QPixmap('images/fullscreen.png'))

        self._speed_buttons = list(SpeedButton(speed) for speed in [0.5, 1.5, 3])

        self._submit_button = QPushButton(' Send for Review ')
        self._submit_button.setFixedWidth(190)
        self._submit_button.setDisabled(True)
        self._submit_button.setVisible(False)
        self._submit_button.setStyleSheet(button_style)

        self._approve_button = QPushButton(' Accept assignment ')
        self._approve_button.setFixedWidth(190)
        self._approve_button.setDisabled(True)
        self._approve_button.setVisible(False)
        self._approve_button.setStyleSheet(button_style)

        self._reject_button = QPushButton(' Reject assignment ')
        self._reject_button.setFixedWidth(190)
        self._reject_button.setDisabled(True)
        self._reject_button.setVisible(False)
        self._reject_button.setStyleSheet(button_style)

        self._observation_table = ObservationTable(self)

        # An annotation session is in the context of a set.  Track the current set we're annotating
        self.current_set = None
        self.setup_layout()
        self.wire_events()
        # multi key press event handling set
        self.keylist = set()
        self.firstrelease = None
        # installing eventFilter for controlling sat/brightness popup hide and show
        QCoreApplication.instance().installEventFilter(self)

    def wire_events(self):
        self._toggle_play_button.clicked.connect(self.on_toggle_play)
        self._submit_button.clicked.connect(self.on_submit)
        self._approve_button.clicked.connect(self.on_accept)
        self._reject_button.clicked.connect(self.on_reject)
        self._rew_button.clicked.connect(self.on_rewind)
        self._ff_button.clicked.connect(self.on_fast_forward)
        self._step_back_button.clicked.connect(self.on_step_back)
        self._step_forward_button.clicked.connect(self.on_step_forward)
        self._back15.clicked.connect(self.on_back15)
        self._back05.clicked.connect(self.on_back05)

        self._filter_widget.change.connect(self.on_filter_change)
        self._video_filter_button.clicked.connect(self.on_video_filter_button)
        self._fullscreen_button.clicked.connect(self.on_fullscreen)

        self._video_player.playStateChanged.connect(self.on_playstate_changed)
        self._video_player.progressUpdate.connect(self.on_progress_update)
        self._video_player.playbackSpeedChanged.connect(self.on_playback_speed_changed)

        self._slider.tickSelected.connect(self.on_slider_tick)

        self._observation_table.durationClicked.connect(self.set_duration)
        self._observation_table.goToEvent.connect(self.event_selected)

        self._observation_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._observation_table.customContextMenuRequested.connect(self._observation_table.customContextMenu)
        self._observation_table.tableRefresh.connect(self.onTableRefresh)

        for button in self._speed_buttons:
            button.speedClick.connect(self.on_speed)

        self.keyPressed.connect(self.on_key)

    def setup_layout(self):
        # Main container going top to bottom
        container = QVBoxLayout()
        container.setDirection(QBoxLayout.TopToBottom)

        # Top section L/R
        top_box = QHBoxLayout()

        # Video screen and slider
        vid_box = QVBoxLayout()
        vid_box.addWidget(self._video_label)
        vid_box.addWidget(self._video_player)

        vid_box.addWidget(self._slider)

        pos_layout = QHBoxLayout()
        pos_layout.addWidget(self._pos_label)  # TODO move this under the cursor
        pos_layout.addWidget(self._playback_speed_label)
        pos_layout.addStretch(1)
        pos_layout.addWidget(self._duration_label)

        vid_box.addLayout(pos_layout)
        vid_box.addStretch(1)

        # add to top box
        top_box.addLayout(vid_box)

        # Video controls
        video_controls_box = QHBoxLayout()
        video_controls_box.addSpacing(25)

        #video_controls_box.addWidget(self._rew_button)
        video_controls_box.addWidget(self._back15)
        video_controls_box.addWidget(self._back05)
        video_controls_box.addWidget(self._step_back_button)
        video_controls_box.addWidget(self._toggle_play_button)
        video_controls_box.addWidget(self._step_forward_button)
        video_controls_box.addWidget(self._ff_button)
        video_controls_box.addSpacing(40)
        for button in self._speed_buttons:
            video_controls_box.addWidget(button)
        video_controls_box.addStretch(1)

        # Secondary controls
        secondary_controls_box = QHBoxLayout()
        secondary_controls_box.addSpacing(25)
        #secondary_controls_box.addWidget(self._video_filter_label)
        secondary_controls_box.addWidget(self._video_filter_button)
        secondary_controls_box.addWidget(self._fullscreen_button)
        secondary_controls_box.addStretch(1)

        # Buttons
        button_box = QVBoxLayout()
        button_box.setDirection(QBoxLayout.BottomToTop)
        button_box.addLayout(video_controls_box)
        button_box.addLayout(secondary_controls_box)
        button_box.addWidget(self._submit_button)
        button_box.addStretch(1)
        button_box.addWidget(self._reject_button)
        button_box.addWidget(self._approve_button)

        # add to top box
        top_box.addLayout(button_box)

        # add top box to main layout
        container.addLayout(top_box)

        # Observation table
        bottom_box = QVBoxLayout()
        header = QLabel()
        header.setStyleSheet("""background-color: rgb(41, 86, 109);color: rgb(255, 255, 255);font: 75 18pt "Arial";""")
        header.setText("   Observations")
        header.setMinimumHeight(40)
        bottom_box.addWidget(header)

        bottom_box.addWidget(self._observation_table)
        container.addLayout(bottom_box)
        self.setLayout(container)

    @staticmethod
    def get_local_file(orig_file_path):
        path, filename = os.path.split(orig_file_path)
        local_path = global_config.get('VIDEOS', 'alt_media_dir')
        matching_files = []
        for dir_path, dir_names, file_names in os.walk(local_path):
            for f in file_names:
                if f == filename:
                    matching_files.append(os.path.join(dir_path, f))

        if len(matching_files) == 1:
            return matching_files[0]
        elif len(matching_files) > 1:
            return matching_files[0]  # TODO: Allow selection if there's more than one
        else:
            error_message = 'File not found in local media store.  Using original path {0}'.format(orig_file_path)
            getLogger('finprint').info(error_message)
            return False

    def load_set(self, set):
        getLogger('finprint').info("Loading Set {0}".format(set.code))

        self._data_loading = True
        self.clear()
        self.current_set = set

        self._video_label.setText('{0}'.format(self.current_set.file))

        self._rew_button.setDisabled(False)
        self._back15.setDisabled(False)
        self._back05.setDisabled(False)
        if GlobalFinPrintServer().is_lead():
            self._ff_button.setDisabled(False)
            self._ff_button.setVisible(True)
            if set.status_id == 3:
                self._approve_button.setDisabled(False)
                self._approve_button.setVisible(True)
                self._reject_button.setDisabled(False)
                self._reject_button.setVisible(True)
        if GlobalFinPrintServer().is_assigned_to_self(set) and set.status_id < 3:
            self._submit_button.setVisible(True)

        #change for GLOB-528
        self.check_submit_button_activation_condition(set)


        self._toggle_play_button.setDisabled(False)
        self._step_back_button.setDisabled(False)
        self._step_forward_button.setDisabled(False)

        for button in self._speed_buttons:
            if not GlobalFinPrintServer().is_lead() and button.speed > 1.5:
                button.setVisible(False)

        self._observation_table.set_data()

        file_name = self.get_local_file(set.file)
        if not self._video_player.load(file_name):
            msgbox = QMessageBox()
            msgbox.setText("Could not load file: {0}".format(file_name))
            msgbox.setWindowTitle("Error Loading Video")
            msgbox.exec_()
        self._video_player.load_set(set)

        self._slider.setMaximum(int(self._video_player.get_length()))
        self._slider.load_set(self.current_set)
        self._slider.set_allowed_progress(set.progress)
        self._slider.show()

        self._duration_label.setText(convert_position(self._video_player.get_length()))
        self._playback_speed_label.setText('(0x)')

        self._observation_table.load_set(set)
        self._data_loading = False

    def on_playstate_changed(self, play_state):
        getLogger('finprint').info('layout widget: playstate changed: {0}'.format(play_state))
        if play_state == PlayState.EndOfStream or play_state == PlayState.Paused:
            self.on_progress_update(self._video_player.get_position())  # update position on pause
            self._toggle_play_button.setPixmap(self._play_pixmap)
        else:
            self._toggle_play_button.setPixmap(self._pause_pixmap)

        if play_state == PlayState.EndOfStream and self.current_set.assigned_to_current():
            self._submit_button.setDisabled(False)

    def on_playback_speed_changed(self, speed):
        self._playback_speed_label.setText('({}x)'.format(int(speed) if int(speed) == speed else speed))

    def on_progress_update(self, progress):
        if self.current_set is not None:
            self.current_set.update_progress(progress)

    def clear(self):
        self._video_label.setText('')
        self._slider.hide()
        self._video_player.clear()
        self._submit_button.setDisabled(True)
        self._submit_button.setVisible(False)
        self._approve_button.setDisabled(True)
        self._approve_button.setVisible(False)
        self._reject_button.setDisabled(True)
        self._reject_button.setVisible(False)
        self._rew_button.setDisabled(True)
        self._back15.setDisabled(True)
        self._back05.setDisabled(True)
        self._ff_button.setDisabled(True)
        self._step_forward_button.setDisabled(True)
        self._step_back_button.setDisabled(True)
        self._toggle_play_button.setDisabled(True)
        self._observation_table.empty()
        self.current_set = None

    def on_slider_tick(self, position, obs):
        events = sorted(obs.events, key=lambda e: e.create_datetime)
        self.event_selected(events[0])

    def event_selected(self, evt):
        self._video_player.display_event(evt.event_time, evt.extent)

    def on_toggle_play(self):
        self._video_player.toggle_play()

    def on_submit(self):
        self.current_set.mark_as_done()
        self.clear()
        self._main_window._launch_assign_diag()

    def on_accept(self):
        GlobalFinPrintServer().mark_set_approved(self.current_set.id)
        self.clear()
        self._main_window._launch_assign_diag()

    def on_reject(self):
        GlobalFinPrintServer().mark_set_rejected(self.current_set.id)
        self.clear()
        self._main_window._launch_assign_diag()

    def on_rewind(self):
        self._video_player.rewind()

    ''' Pause the video and Go back 15 seconds '''
    def on_back15(self):
        self._video_player.scrub_position(self._video_player.get_position() - 15000)

    ''' Pause the video and Go back 5 seconds '''
    def on_back05(self):
        self._video_player.scrub_position(self._video_player.get_position() - 5000)

    def on_fast_forward(self):
        self._video_player.fast_forward()

    def on_step_back(self):
        self._video_player.scrub_position(self._video_player.get_position() - self.FRAME_STEP)

    def on_step_forward(self):
        self._video_player.scrub_position(self._video_player.get_position() + self.FRAME_STEP)

    def on_speed(self, speed):
        self._video_player.set_speed(speed)

    def on_quit(self):
        if self._video_player is not None:
            self.on_progress_update(self._video_player.get_position())  # update position on quit
        QCoreApplication.instance().quit()

    def set_duration(self, obs):
        pos = self._video_player.get_position()
        duration = int(pos) - int(obs.initial_time())
        if duration <= 0:
            msgbox = QMessageBox()
            msgbox.setText("Can not set a duration less than zero")
            msgbox.setWindowTitle("Error Setting Duration")
            msgbox.exec_()
        else:
            self.current_set.edit_observation(obs, {'duration': duration})
            self._observation_table.refresh_model()

    def on_organism_cell_changed(self, animal, row):
        obs = self._observation_table.get_observation(row)
        obs.animal_id = animal.id
        obs.animal = animal
        self.current_set.edit_observation(obs)

    def add_observation(self, obs):
        self._data_loading = True
        self.current_set.add_observation(obs)
        self._observation_table.add_row(obs)
        self._data_loading = False
        self._observation_table.scrollToBottom()

    def on_position_change(self, pos):
        self._pos_label.setText(convert_position(pos))
        self._slider.setValue(int(pos))

    def onTableRefresh(self):
        self._slider.load_set(self.current_set)
        self.check_submit_button_activation_condition(self.current_set)

    def on_fullscreen(self):
        self._video_player.pause()
        self._filter_widget.hide()
        self._video_filter_button.setPixmap(QPixmap('images/filters.png'))
        args = [self.current_set,
                self.get_local_file(self.current_set.file),
                self._video_player]
        if self.fullscreen:
            self.fullscreen.revive(*args)
        else:
            self.fullscreen = FullScreen(*args)
        self.is_fullscreen = True

    def on_video_filter_button(self):
        img = self._filter_widget.toggle(self._video_filter_button)
        self._video_filter_button.setPixmap(QPixmap(img))

    def on_filter_change(self, saturation, brightness, contrast):
        self._video_player.saturation = saturation
        self._video_player.brightness = brightness
        self._video_player.contrast = contrast
        if self._video_player.is_paused():
            self._video_player.refresh_frame()

    def check_submit_button_activation_condition(self, set):
        #instead of having constant for mark_haul_time,mark_90Mins_time
        #we are fetcheing by row number from sets.attributes which is pulled directly from database
        #which its always constant
        #taking id or MARK_HAUL_TIME_GLOBAL_ID=23 and MARK_90_MIN_GLOBAL_ID = 24
        #set.attributes = {list} <class 'list'>:
        for observation in set.observations :
           for events in observation.events:
               for attribute in events.attribute :
                   if "global_parent_id" in attribute and attribute["global_parent_id"] in [MARK_HAUL_TIME_GLOBAL_ID, MARK_90_MIN_GLOBAL_ID] :
                        self._submit_button.setDisabled(False)
                        return True

        self._submit_button.setDisabled(True)
        return False

    def keyPressEvent(self, event):
        '''
        overriding system keyPressEvent to handle multikey press
        '''
        super(VideoLayoutWidget, self).keyPressEvent(event)
        self.firstrelease = True
        self.keylist.add(event.key())
        self.keyPressed.emit(event)

    def on_key(self, event):
        if event.key() == Qt.Key_F5:
            self.on_fullscreen()

    def keyReleaseEvent(self, evt):
        '''
        overriding system keyReleaseEvent ,
        adds keyEvent in keyList when later key is
        released in case of multi key press
        '''
        super(VideoLayoutWidget, self).keyReleaseEvent(evt)
        if self.firstrelease == True:
            self.keylist.add(evt.key())
            MultiKeyPressHandler().process_multi_key_press(self)

        self.firstrelease = False
        if self.keylist :
            self.keylist.pop()

    def eventFilter(self, source, evt):
        if evt.type() == QEvent.KeyPress and source is not self._video_filter_button \
           and QApplication.activeModalWidget() is None:
            # handles keyboard shortcut
            self.keyboard_shortcut_event(evt)
        elif evt.type() == QEvent.MouseButtonPress and QApplication.activeModalWidget() is None:
            # event capture for mouse click
            self.setFocus()

        return False

    def keyboard_shortcut_event(self, evt):
        '''
        Considering that keyboard shortcut in windows
        as per explained is anything which involves shift modifier
        or control modifier or both or F1.
        '''
        if self._filter_widget.isVisible():
            MultiKeyPressHandler().handle_keyboard_shortcut_event(evt, self._filter_widget)




