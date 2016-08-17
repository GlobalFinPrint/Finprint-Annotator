import os
from logging import getLogger
from video_player import CvVideoWidget, PlayState
from global_finprint import GlobalFinPrintServer
from config import global_config
from .video_seek_widget import VideoSeekWidget
from .observation_table import ObservationTable
from .util import convert_position
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class ClickLabel(QLabel):
    clicked = pyqtSignal()

    def mouseReleaseEvent(self, ev):
        self.emit(SIGNAL('clicked()'))


class VideoLayoutWidget(QWidget):
    def __init__(self, main_window):
        super(VideoLayoutWidget, self).__init__()

        self._main_window = main_window

        # UI widgets
        self.vid_box = None
        self._video_label = QLabel('')
        self._video_label.setStyleSheet("""color:rgb(74,74,74); font: 75 12pt "Arial";""")
        self._video_player = CvVideoWidget(parent=self, onPositionChange=self.on_position_change)
        self._pos_label = QLabel()
        self._duration_label = QLabel()
        self._data_loading = False

        self._play_pixmap = QPixmap('images/video_control-play.png')
        self._pause_pixmap = QPixmap('images/video_control-pause.png')

        self._slider = VideoSeekWidget(self._video_player)
        self._slider.hide()

        self._rew_button = ClickLabel()
        self._rew_button.setPixmap(QPixmap('images/video_control-rewind.png'))

        self._ff_button = ClickLabel()
        self._ff_button.setPixmap(QPixmap('images/video_control-fast_forward.png'))
        self._ff_button.setVisible(False)

        self._step_back_button = ClickLabel()
        self._step_back_button.setPixmap(QPixmap('images/video_control-step_back.png'))

        self._toggle_play_button = ClickLabel()
        self._toggle_play_button.setPixmap(self._play_pixmap)

        self._step_forward_button = ClickLabel()
        self._step_forward_button.setPixmap(QPixmap('images/video_control-step_forward.png'))

        self._submit_button = QPushButton('Send for Review')
        self._submit_button.setFixedWidth(190)
        self._submit_button.setDisabled(True)
        self._submit_button.setStyleSheet("""QPushButton {  background: rgb(41, 86, 109); color:white; font: 12pt "Arial";
                                                            border-radius: 4px; padding-top: 4px; padding-bottom: 4px; padding-left:
                                                            5px; padding-right: 5px;}

                                            QPushButton:hover {background: rgb(41, 86, 109, 128)}

                                            QPushButton:disabled {background: rgb(131,140,158, 128);
                                                                    color:white;}

                                            """)

        self._obs_btn_box = QHBoxLayout()

        self.organism_selector_button = None
        self.organism_selector_table = None

        self._observation_table = ObservationTable(self)

        self.grouping = {}

        # An annotation session is in the context of a set.  Track the current set we're annotating
        self.current_set = None

        self.setup_layout()
        self.wire_events()

    def wire_events(self):
        self._toggle_play_button.clicked.connect(self.on_toggle_play)
        self._submit_button.clicked.connect(self.on_submit)
        self._rew_button.clicked.connect(self.on_rewind)
        self._ff_button.clicked.connect(self.on_fast_forward)
        self._step_back_button.clicked.connect(self.on_step_back)
        self._step_forward_button.clicked.connect(self.on_step_forward)

        self._video_player.playStateChanged.connect(self.on_playstate_changed)
        self._video_player.progressUpdate.connect(self.on_progress_update)

        self._observation_table.durationClicked.connect(self.set_duration)
        self._observation_table.goToEvent.connect(self.event_selected)

        self._observation_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._observation_table.customContextMenuRequested.connect(self._observation_table.customContextMenu)

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
        pos_layout.addWidget(self._duration_label, alignment=Qt.AlignRight)
        vid_box.addLayout(pos_layout)
        vid_box.addStretch(1)

        # add to top box
        top_box.addLayout(vid_box)

        # Video controls
        video_controls_box = QHBoxLayout()
        video_controls_box.addWidget(self._rew_button)
        video_controls_box.addWidget(self._step_back_button)
        video_controls_box.addWidget(self._toggle_play_button)
        video_controls_box.addWidget(self._step_forward_button)
        video_controls_box.addWidget(self._ff_button)

        # Buttons
        button_box = QVBoxLayout()
        button_box.setDirection(QBoxLayout.BottomToTop)
        button_box.addLayout(video_controls_box)
        button_box.addWidget(self._submit_button)
        button_box.addStretch(1)

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

    def clear_buttons(self):
        for idx in reversed(range(self._obs_btn_box.count())):
            widget = self._obs_btn_box.takeAt(idx).widget()
            if widget is not None:
                widget.deleteLater()

    def get_local_file(self, orig_file_path):
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
            return matching_files[0] #TODO: Allow selection if there's more than one
        else:
            error_message = 'File not found in local media store.  Using original path {0}'.format(orig_file_path)
            getLogger('finprint').info(error_message)
            return orig_file_path

    def load_set(self, set):
        getLogger('finprint').info("Loading Set {0}".format(set.code))

        self._data_loading = True
        self.clear()
        self.current_set = set

        self._video_label.setText('{0}'.format(self.current_set.file))

        self._rew_button.setDisabled(False)
        if GlobalFinPrintServer().is_lead():
            self._ff_button.setDisabled(False)
            self._ff_button.setVisible(True)
        self._toggle_play_button.setDisabled(False)
        self._step_back_button.setDisabled(False)
        self._step_forward_button.setDisabled(False)

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

        self._observation_table.load_set(set)
        self._data_loading = False

    def on_playstate_changed(self, play_state):
        if play_state == PlayState.EndOfStream or play_state == PlayState.Paused:
            self.on_progress_update(self._video_player.get_position())  # update position on pause
            self._toggle_play_button.setPixmap(self._play_pixmap)
        else:
            self._toggle_play_button.setPixmap(self._pause_pixmap)

        if play_state == PlayState.EndOfStream and self.current_set.assigned_to_current():
            self._submit_button.setDisabled(False)

    def on_progress_update(self, progress):
        if self.current_set is not None:
            self.current_set.update_progress(progress)

    def clear(self):
        self._video_label.setText('')
        self._slider.hide()
        self._video_player.clear()
        self.clear_buttons()
        self._submit_button.setDisabled(True)
        self._rew_button.setDisabled(True)
        self._ff_button.setDisabled(True)
        self._step_forward_button.setDisabled(True)
        self._step_back_button.setDisabled(True)
        self._toggle_play_button.setDisabled(True)
        self._observation_table.empty()
        self.current_set = None

    def event_selected(self, evt):
        self._video_player.pause()
        self._video_player.display_event(evt.event_time, evt.extent)

    def on_toggle_play(self):
        self._video_player.toggle_play()

    def on_submit(self):
        self.current_set.mark_as_done()
        self.clear()
        self._main_window._launch_set_list()

    def on_rewind(self):
        self._video_player.rewind()

    def on_fast_forward(self):
        self._video_player.fast_forward()

    def on_step_back(self):
        self._video_player.step_back()

    def on_step_forward(self):
        self._video_player.step_forward()

    def on_quit(self):
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
