import sys, os
import os.path
from math import floor
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from video_player import CvVideoWidget
from global_finprint import Observation, Set
from config import global_config
from logging import getLogger

class VideoSeekWidget(QSlider):
    def __init__(self, player):
        super(VideoSeekWidget, self).__init__()

        self._player = player

        self.setOrientation(Qt.Horizontal)
        self.setStyleSheet(self.style())

        self.sliderPressed.connect(self._pressed)
        #self.sliderMoved.connect(self._moved)
        self.sliderReleased.connect(self._released)

    def _pressed(self):
        self._player.pause()

    #def _moved(self, pos):
    #    pass
        #self._player.set_position(pos)

    def _released(self):
        self._player.set_position(self.value())
        self._player.play()

    def setMaximum(self, value):
        super(VideoSeekWidget, self).setMaximum(value)
        max = self.maximum()
        pass

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


class MenuButton(QPushButton):
    item_select = pyqtSignal(dict)

    def __init__(self, menuDict, *args, **kw):
        QPushButton.__init__(self, *args, **kw)
        self.last_mouse_pos = None
        self.menus = []
        self.menu_dict = menuDict
        self.clicked.connect(self.popup_menu)

    def mousePressEvent(self, event):
        self.last_mouse_pos = event.pos()
        QPushButton.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        self.last_mouse_pos = event.pos()
        QPushButton.mouseReleaseEvent(self, event)

    def get_last_pos(self):
        if self.last_mouse_pos:
            return self.mapToGlobal(self.last_mouse_pos)
        else:
            return None

    def popup_menu(self):
        def _make_action(data):
            return lambda: self.item_select.emit(data)

        top_menu = QMenu('Organisms')
        for group in self.menu_dict:
            obsmenu = QMenu(group)
            for animal in self.menu_dict[group]:
                title = "{0} ({1} {2})".format(animal['common_name'], animal['genus'], animal['species'])
                obsmenu.addAction(title).triggered.connect(_make_action(animal))
            self.menus.append(obsmenu)
            top_menu.addMenu(obsmenu)

        top_menu.exec_(self.get_last_pos())


class VideoLayoutWidget(QWidget):
    def __init__(self):
        super(VideoLayoutWidget, self).__init__()

        # UI widgets
        self.vid_box = None
        self._video_player = CvVideoWidget(onPositionChange=self.on_position_change)
        self._pos_label = QLabel()

        self._slider = VideoSeekWidget(self._video_player)
        self._rew_icon = QIcon('images/rewind.png')
        self._pause_icon = QIcon('images/pause.png')
        self._play_icon = QIcon('images/play.png')
        self._process_icon = QIcon('images/clapperboard.png')

        self._rew_button = QPushButton('')
        self._rew_button.setIcon(self._rew_icon)

        self._pause_button = QPushButton('')
        self._pause_button.setIcon(self._play_icon)
        self._pause_button.setText('Resume')

        self._process_button = QPushButton('Process')
        self._process_button.setIcon(self._process_icon)

        self._obs_btn_box = QHBoxLayout()

        self._quit_button = QPushButton('Quit')
        self._observation_table = ObservationTable(self.delete_observation)

        self.grouping = {}


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
        self._rew_button.clicked.connect(self.on_rewind)
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
        vid_btn_box.addWidget(self._rew_button )
        vid_btn_box.addWidget(self._pause_button )
        #vid_btn_box.addWidget(self._process_button)

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

    def clear_buttons(self):
        for idx in reversed(range(self._obs_btn_box.count())):
            widget = self._obs_btn_box.takeAt(idx).widget()
            if widget is not None:
                widget.deleteLater()

    def load_buttons(self, animals):
        # Video control and observation register buttons
        self.grouping = {}
        for animal in animals:
            if animal['group'] not in self.grouping:
                self.grouping[animal['group']] = []
            self.grouping[animal['group']].append(animal)

        self.critter_button = MenuButton(self.grouping, "Organisms")
        self.critter_button.item_select.connect(self.on_observation)
        self._obs_btn_box.addWidget(self.critter_button)

        self._of_interest = QPushButton('Of Interest')
        self._of_interest.clicked.connect(self.of_interest)
        self._obs_btn_box.addWidget(self._of_interest)

    def get_local_file(self, orig_file_name):
        (dir, file_name) = os.path.split(orig_file_name)
        search_dir = global_config.get('VIDEOS', 'alt_media_dir')
        for root, dirnames, filenames in os.walk(search_dir):
            for filename in filenames:
                if filename.lower() == file_name.lower():
                    return os.path.join(root, filename)

        getLogger('finprint').info('File not found in local media store.  Using original path {0}'.format(orig_file_name))
        return orig_file_name

    def load_set(self, set):
        self.clear()
        self.current_set = set
        self.load_buttons(set.animals)

        file_name = self.get_local_file(set.file)
        if not self._video_player.load(file_name):
            msgbox = QMessageBox()
            msgbox.setText("Could not load file: {0}".format(file_name))
            #msgbox.setInformativeText("working dir: {0}\nreal dir: {1}".format(os.getcwd(), os.path.dirname(os.path.realpath(__file__))))
            msgbox.setWindowTitle("Error Loading Video")
            msgbox.exec_()

        self._slider.setMaximum(int(self._video_player.get_length()))

        for obs in set.observations:
            self._observation_table.add_row(obs)

    def clear(self):
        self._video_player.clear()
        self.clear_buttons()
        self._observation_table.setRowCount(0)
        self.current_set = None

    def observation_selected(self, selected, deselected):
        obs = self._observation_table.get_observation(self._observation_table.currentRow())
        if hasattr(obs, 'rect'):
            self._video_player.display_observation(obs.initial_observation_time, obs.rect)

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

    def on_rewind(self):
        self._video_player.rewind()

    def on_observation(self, data):
        obs = Observation()
        obs.animal_id = data['id']
        obs.species = data['common_name']
        obs.initial_observation_time = int(self._video_player.get_position())
        #obs.display_position = self._convert_position(obs.position)
        obs.rect = self._video_player.get_highlight()
        self.add_observation(obs)

    def of_interest(self):
        obs = Observation()
        obs.position = self._video_player.get_position()
        obs.initial_observation_time = int(self._video_player.get_position())
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
        #s, m = divmod(floor(pos), 1000)
        self._slider.setValue(int(pos))


class ObservationTable(QTableWidget):
    column_headers = ['Time', 'Species', 'Duration', 'Notes']

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
        self.setColumnWidth(1, 250)
        self.setColumnWidth(3, 400)
        #self.setColumnCount(self.columnCount() + 1)


    def get_observation(self, row):
        return self._observations[row]

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        set_duration_action = menu.addAction("Set Duration")
        row = self.indexAt(event.pos()).row()
        if row >= 0:
            action = menu.exec_(event.globalPos())
            if action == delete_action:
                self.delete_callback(self._observations[row])
                self._observations.pop(row)
                self.removeRow(row)
            if action == set_duration_action:
                pass
                #self.setItem(row, 2, QTableWidgetItem('1200'))


    def add_row(self, obs):
        new_row_index = self.rowCount()
        self.setRowCount(new_row_index + 1)
        self.setItem(new_row_index, 0, QTableWidgetItem(str(obs.initial_observation_time)))
        self.setItem(new_row_index, 1, QTableWidgetItem(obs.animal))
        self.setItem(new_row_index, 3, QTableWidgetItem(obs.comment))

        self._observations.insert(new_row_index, obs)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    widget = CvVideoWidget()
    widget.setWindowTitle('PyQt - OpenCV Test')
    widget.show()

    sys.exit(app.exec_())
