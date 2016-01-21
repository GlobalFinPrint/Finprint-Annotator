import sys
from math import floor
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from video_player import CvVideoWidget
from global_finprint import Observation, Set


class VideoSeekWidget(QSlider):
    def __init__(self):
        super(VideoSeekWidget, self).__init__()

        self.setOrientation(Qt.Horizontal)
        self.setStyleSheet(self.style())

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

class VideoLayoutWidget(QWidget):
    def __init__(self):
        super(VideoLayoutWidget, self).__init__()

        # UI widgets
        self.vid_box = None
        self._video_player = CvVideoWidget(onPositionChange=self.on_position_change)
        self._pos_label = QLabel()

        self._slider = VideoSeekWidget()
        self._pause_icon = QIcon('images/pause.png')
        self._play_icon = QIcon('images/play.png')
        self._process_icon = QIcon('images/clapperboard.png')

        self._pause_button = QPushButton('Resume')
        self._pause_button.setIcon(self._play_icon)

        self._process_button = QPushButton('Process')
        self._process_button.setIcon(self._process_icon)

        self._obs_btn_box = QHBoxLayout()

        self._quit_button = QPushButton('Quit')
        self._observation_table = ObservationTable(self.delete_observation)

        # An annotation seession is in the context of a set.  Track the current set we're annotating
        self.current_set = None

        # Buttons to record an observation of a registered species
        #  This will be dynamic based on each annotation session
        #self._species_buttons = ['Grey Reef', 'Nurse', 'Tiger', 'Jaws']

        self.setup_layout()
        self.wire_events()


    def wire_events(self):
        self._quit_button.clicked.connect(QCoreApplication.instance().quit)
        self._pause_button.clicked.connect(self.on_pause)
        self._process_button.clicked.connect(self.on_process)
        self._observation_table.selectionChanged = self.observation_selected

    def setup_layout(self):
        # Main container going top to bottom
        container = QVBoxLayout()
        container.setDirection(QBoxLayout.TopToBottom)

        # Main Video Window
        self.vid_box = QHBoxLayout()
        self.vid_box.addWidget(self._video_player)
        container.addLayout(self.vid_box)

        # Seek bar
        seek_bar_box = QHBoxLayout()
        seek_bar_box.addWidget(self._slider)

        container.addLayout(seek_bar_box)

        # Video control and observation register buttons
        vid_btn_box = QHBoxLayout()
        vid_btn_box.addStretch(1)
        vid_btn_box.addWidget(self._pos_label)
        vid_btn_box.addWidget(self._pause_button )
        vid_btn_box.addWidget(self._process_button)

        btn_box = QHBoxLayout()
        btn_box.addLayout(self._obs_btn_box)
        btn_box.addLayout(vid_btn_box)

        container.addLayout(btn_box)

        # Observation table
        table_box = QHBoxLayout()
        table_box.addWidget(self._observation_table )
        container.addLayout(table_box)

        # App buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch(1)
        btn_box.addWidget(self._quit_button )
        container.addLayout(btn_box)

        self.setLayout(container)

    def load_buttons(self, animals):
        # Video control and observation register buttons
        for animal in animals:
            obsbtn = QPushButton(animal['common_name'])
            obsbtn.data = animal
            obsbtn.clicked.connect(self.on_observation)

            self._obs_btn_box.addWidget(obsbtn, alignment=Qt.AlignLeft)

        self._of_interest = QPushButton('Of Interest')
        self._of_interest.clicked.connect(self.of_interest)
        self._obs_btn_box.addWidget(self._of_interest)

    def load_set(self, set):
        self.current_set = set
        self.load_buttons(set.animals)
        ### TODO: fix absolute path issues
        file_name = 'c:/temp/' + set.file[2:len(set.file)]
        self._video_player.load(file_name)
        self._slider.setMaximum(int(self._video_player.get_length()))

        for obs in set.observations:
            self._observation_table.add_row(obs)

    def clear(self):
        self._video_player.clear()
        self.current_set = None

    def observation_selected(self, selected, deselected):
        obs = self._observation_table.get_observation(self._observation_table.currentRow())
        if hasattr(obs, 'rect'):
            self._video_player.display_observation(obs.position, obs.rect)

    def on_pause(self):
        if self._video_player.paused():
            self._video_player.play()
            self._pause_button.setText('Pause')
            self._pause_button.setIcon(self._pause_icon)
        else:
            self._video_player.pause()
            self._pause_button.setText('Resume')
            self._pause_button.setIcon(self._play_icon)

    def on_process(self):
        self._video_player.fast_forward()

    def on_observation(self, event):
        btn = self.sender()
        data = btn.data
        obs = Observation()
        obs.animal_id = data['id']
        obs.species = self.sender().text()
        obs.position = self._video_player.get_position()
        obs.display_position = self._convert_position(obs.position)
        obs.rect = self._video_player.get_highlight()
        self.add_observation(obs)

    def of_interest(self):
        obs = Observation()
        obs.position = self._video_player.get_position()
        obs.display_position = self._convert_position(obs.position)
        obs.rect = self._video_player.get_highlight()
        dlg = QInputDialog(self)
        dlg.setInputMode(QInputDialog.TextInput)
        note, ok = dlg.getText(self, 'Observation of Interest', 'Please enter detail of your observation')
        if ok:
            obs.notes = note
            self.add_observation(obs)

    def add_observation(self, obs):
        self.current_set.add_observation(obs)
        self._observation_table.add_row(obs)

    def delete_observation(self, obs):
        self.current_set.delete_observation(obs)

    def _convert_position(self, pos):
        s, m = divmod(floor(pos), 1000)
        h, s = divmod(s, 60)
        return "{0:02}:{1:02}:{2:03}".format(h, s, m)

    def on_position_change(self, pos):
        self._pos_label.setText(self._convert_position(pos))
        s, m = divmod(floor(pos), 1000)
        self._slider.setValue(s)


class ObservationTable(QTableWidget):
    column_headers = ['Time', 'Species', 'Notes']

    def __init__(self, delete_callback, *args):
        super(ObservationTable, self).__init__(*args)
        # Track the rectangle highlights for each observation
        self.delete_callback = delete_callback
        self._observations = []
        self.set_data()
        self.show()
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    def set_data(self):
        self.setColumnCount(len(ObservationTable.column_headers))
        self.setHorizontalHeaderLabels(ObservationTable.column_headers)

    def get_observation(self, row):
        return self._observations[row]

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        row = self.indexAt(event.pos()).row()
        if row >= 0:
            action = menu.exec_(event.globalPos())
            if action == delete_action:
                self.delete_callback(self._observations[row])
                self._observations.pop(row)
                self.removeRow(row)



    def add_row(self, obs):
        new_row_index = self.rowCount()
        self.setRowCount(new_row_index + 1)
        self.setItem(new_row_index, 0, QTableWidgetItem(obs.initial_observation_time.strftime('%Y-%m-%dT%I:%M:%S.%fZ')))
        self.setItem(new_row_index, 1, QTableWidgetItem(obs.animal))
        self.setItem(new_row_index, 2, QTableWidgetItem(obs.comment))

        self._observations.insert(new_row_index, obs)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    widget = CvVideoWidget()
    widget.setWindowTitle('PyQt - OpenCV Test')
    widget.show()

    sys.exit(app.exec_())
