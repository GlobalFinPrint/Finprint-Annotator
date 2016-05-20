import sys
import os
from enum import IntEnum
from math import floor
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from video_player import CvVideoWidget, PlayState
from global_finprint import Observation, Animal, GlobalFinPrintServer
from config import global_config
from logging import getLogger


def convert_position(pos):
    s, m = divmod(floor(pos), 1000)
    h, s = divmod(s, 60)
    return "{0:02}:{1:02}:{2:03}".format(h, s, m)




class VideoSeekWidget(QSlider):
    item_select = pyqtSignal(Animal)

    def __init__(self, player):
        super(VideoSeekWidget, self).__init__()

        self.dragging = False
        self._player = player
        self.setOrientation(Qt.Horizontal)
        self.setStyleSheet(self.style())
        self.allowed_progress = None

        self.sliderPressed.connect(self._pressed)
        self.sliderMoved.connect(self._moved)
        self.sliderReleased.connect(self._released)

    def _pressed(self):
        self.dragging = True
        self.allowed_progress = max(self.value(), self.allowed_progress)
        self._player.pause()

    def _moved(self, pos):
        QToolTip.showText(QCursor.pos(), convert_position(pos))

    def _released(self):
        self.dragging = False
        # do not allow fast forward for non-leads
        if GlobalFinPrintServer().is_lead() or self.allowed_progress is None:
            self._player.set_position(self.value())
        else:
            self._player.set_position(min(self.value(), self.allowed_progress))

    def setMaximum(self, value):
        super(VideoSeekWidget, self).setMaximum(value)

    def set_allowed_progress(self, progress):
        self.allowed_progress = progress

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
    item_select = pyqtSignal(Animal)

    def __init__(self, *args, **kw):
        QPushButton.__init__(self, *args, **kw)
        self.last_mouse_pos = None

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


class OrganismSelector(QObject):
    item_select = pyqtSignal(Animal, int)

    def __init__(self, animal_menu):
        super(QObject, self).__init__()
        self.menus = []
        self.animal_menu = animal_menu

    def popup_menu(self, pos, row = -1):
        def _make_action(data, row):
            return lambda: self.item_select.emit(data, row)

        top_menu = QMenu('Organisms')
        for group in self.animal_menu:
            obsmenu = QMenu(group)
            for animal in self.animal_menu[group]:
                obsmenu.addAction(str(animal)).triggered.connect(_make_action(animal, row))
            self.menus.append(obsmenu)
            top_menu.addMenu(obsmenu)

        top_menu.exec_(pos)


class VideoLayoutWidget(QWidget):
    def __init__(self, main_window):
        super(VideoLayoutWidget, self).__init__()

        self._main_window = main_window

        # UI widgets
        self.vid_box = None
        self._video_player = CvVideoWidget(onPositionChange=self.on_position_change)
        self._pos_label = QLabel()
        self._data_loading = False

        self._slider = VideoSeekWidget(self._video_player)
        self._rew_icon = QIcon('images/rewind.png')
        self._pause_icon = QIcon('images/pause.png')
        self._play_icon = QIcon('images/play.png')

        self._rew_button = QPushButton('')
        self._rew_button.setIcon(self._rew_icon)

        self._toggle_play_button = QPushButton('')
        self._toggle_play_button.setIcon(self._play_icon)
        self._toggle_play_button.setText('Play')

        self._submit_button = QPushButton('Submit for Review')
        self._submit_button.setDisabled(True)

        self._obs_btn_box = QHBoxLayout()

        self.organism_selector_button = None
        self.critter_button = None

        self._quit_button = QPushButton('Quit')
        self._observation_table = ObservationTable()

        self.grouping = {}

        # An annotation session is in the context of a set.  Track the current set we're annotating
        self.current_set = None

        self.setup_layout()
        self.wire_events()

    def wire_events(self):
        self._quit_button.clicked.connect(self.on_quit)
        self._toggle_play_button.clicked.connect(self.on_toggle_play)
        self._submit_button.clicked.connect(self.on_submit)
        self._rew_button.clicked.connect(self.on_rewind)

        self._video_player.playStateChanged.connect(self.on_playstate_changed)
        self._video_player.progressUpdate.connect(self.on_progress_update)

        self._observation_table.observationRowDeleted.connect(self.delete_observation)
        self._observation_table.durationClicked.connect(self.set_duration)
        self._observation_table.goToObservation.connect(self.observation_selected)
        self._observation_table.cellClicked.connect(self.on_table_cell_click)
        self._observation_table.observationUpdated.connect(self.on_observation_updated)

        self._observation_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._observation_table.customContextMenuRequested.connect(self._observation_table.customContextMenu)

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
        vid_btn_box.addWidget(self._rew_button)
        vid_btn_box.addWidget(self._toggle_play_button)
        vid_btn_box.addWidget(self._submit_button)

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
        btn_box.addWidget(self._quit_button)
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
            if animal.group not in self.grouping:
                self.grouping[animal.group] = []
            self.grouping[animal.group].append(animal)

        self.critter_button = MenuButton("Organisms")
        self.critter_button.clicked.connect(self.menu_button_click)

        # <sigh> Creating two instances of the selector at the moment to
        # better track where it was used from (button or table cell)
        self.organism_selector_button = OrganismSelector(self.grouping)
        self.organism_selector_button.item_select.connect(self.on_observation)

        self.organism_selector_table = OrganismSelector(self.grouping)
        self.organism_selector_table.item_select.connect(self.on_organism_cell_changed)

        self._obs_btn_box.addWidget(self.critter_button)

        self._of_interest = QPushButton('Of Interest')
        self._of_interest.clicked.connect(self.of_interest)
        self._obs_btn_box.addWidget(self._of_interest)

    def menu_button_click(self, evt):
        self._video_player.pause()
        self.organism_selector_button.popup_menu(self.critter_button.get_last_pos())

    def get_local_file(self, orig_file_name):
        os_filename = os.path.join(*orig_file_name.split('/'))
        os_path = os.path.join(global_config.get('VIDEOS', 'alt_media_dir'), os_filename)
        if os.path.isfile(os_path):
            return os_path
        else:
            error_message = 'File not found in local media store.  Using original path {0}'.format(orig_file_name)
            getLogger('finprint').info(error_message)
            return os_filename

    def load_set(self, set):
        getLogger('finprint').info("Loading Set {0}".format(set.code))

        self._data_loading = True
        self.clear()
        self.current_set = set

        self._rew_button.setDisabled(False)
        self._toggle_play_button.setDisabled(False)
        self.load_buttons(set.animals)

        self._observation_table.set_data()

        file_name = self.get_local_file(set.file)
        if not self._video_player.load(file_name):
            msgbox = QMessageBox()
            msgbox.setText("Could not load file: {0}".format(file_name))
            #msgbox.setInformativeText("working dir: {0}\nreal dir: {1}".format(os.getcwd(), os.path.dirname(os.path.realpath(__file__))))
            msgbox.setWindowTitle("Error Loading Video")
            msgbox.exec_()

        self._slider.setMaximum(int(self._video_player.get_length()))
        self._slider.set_allowed_progress(set.progress)

        for obs in set.observations:
            self._observation_table.add_row(obs)
        self._data_loading = False

    def on_playstate_changed(self, play_state):
        if play_state == PlayState.EndOfStream or play_state == PlayState.Paused:
            self.on_progress_update(self._video_player.get_position())  # update position on pause
            self._toggle_play_button.setText('Play')
            self._toggle_play_button.setIcon(self._play_icon)
        else:
            self._toggle_play_button.setText('Pause')
            self._toggle_play_button.setIcon(self._pause_icon)

        if play_state == PlayState.EndOfStream and self.current_set.assigned_to_current():
            self._submit_button.setDisabled(False)

    def on_progress_update(self, progress):
        if self.current_set is not None:
            self.current_set.update_progress(progress)

    def clear(self):
        self._video_player.clear()
        self.clear_buttons()
        self._submit_button.setDisabled(True)
        self._rew_button.setDisabled(True)
        self._toggle_play_button.setDisabled(True)
        self._observation_table.empty()
        self.current_set = None

    def observation_selected(self, obs):
        self._video_player.pause()
        self._video_player.display_observation(obs.initial_observation_time, obs.extent)

    def on_toggle_play(self):
        self._video_player.toggle_play()

    def on_submit(self):
        self.current_set.mark_as_done()
        self.clear()
        self._main_window._launch_set_list()

    def on_rewind(self):
        self._video_player.rewind()

    def on_quit(self):
        self.on_progress_update(self._video_player.get_position())  # update position on quit
        QCoreApplication.instance().quit()

    def set_duration(self, observation):
        pos = self._video_player.get_position()
        duration = int(pos) - int(observation.initial_observation_time)
        if duration <= 0:
            msgbox = QMessageBox()
            msgbox.setText("Can not set a duration less than zero")
            msgbox.setWindowTitle("Error Setting Duration")
            msgbox.exec_()
        else:
            observation.duration = duration
            self.current_set.edit_observation(observation)

    def on_observation(self, animal):
        obs = Observation()
        ## Cheese... Still haven't sorted out animal look ups for observations
        obs.animal_id = animal.id
        obs.animal = animal
        obs.initial_observation_time = int(self._video_player.get_position())
        obs.extent = self._video_player.get_highlight_extent()
        self.add_observation(obs)

    def on_organism_cell_changed(self, animal, row):
        obs = self._observation_table.get_observation(row)
        obs.animal_id = animal.id
        obs.animal = animal
        self.current_set.edit_observation(obs)

    def on_table_cell_click(self, row, col):
        if col == self._observation_table.Columns.organism and self._observation_table.item(row, col) != '':
            self.organism_selector_table.popup_menu(QCursor.pos(), row)

    def on_observation_updated(self, obs):
        self.current_set.edit_observation(obs)

    def of_interest(self):
        self._video_player.pause()
        obs = Observation()
        obs.position = self._video_player.get_position()
        obs.initial_observation_time = int(self._video_player.get_position())
        obs.type_choice = "I"
        obs.extent = self._video_player.get_highlight_extent()
        dlg = QInputDialog(self)
        dlg.setInputMode(QInputDialog.TextInput)
        comment, ok = dlg.getText(self, 'Observation of Interest', 'Please enter detail of your observation')
        if ok:
            obs.comment = comment
            self.add_observation(obs)

    def add_observation(self, obs):
        self._data_loading = True
        self.current_set.add_observation(obs)
        self._observation_table.add_row(obs)
        self._data_loading = False
        self._observation_table.scrollToBottom()

    def delete_observation(self, obs):
        self.current_set.delete_observation(obs)

    def on_position_change(self, pos):
        self._pos_label.setText(convert_position(pos))
        self._slider.setValue(int(pos))


class ObservationTableModel(QAbstractTableModel):
    observationUpdated = pyqtSignal(Observation)

    class Columns(IntEnum):
        id = 0
        type = 1
        time = 2
        organism = 3
        duration = 4
        notes = 5

    def __init__(self):
        self.rows = []
        self.columns = ['ID', 'Type', 'Time', 'Organism', 'Duration (ms)', 'Notes']
        super(QAbstractTableModel, self).__init__(None)

    def rowCount(self, *args, **kwargs):
        return len(self.rows)

    def columnCount(self, *args, **kwargs):
        return len(self.columns)

    def headerData(self, idx, orientation, role=None):
        return self.columns[idx] \
            if role == Qt.DisplayRole and orientation == Qt.Horizontal \
            else super(QAbstractTableModel, self).headerData(idx, orientation, role)

    def data(self, model_index, role=None):
        return self.rows[model_index.row()].to_columns()[model_index.column()] \
            if role in [Qt.DisplayRole, Qt.EditRole] \
            else None

    def setData(self, model_index, value, role=None):
        if role == Qt.EditRole and model_index.column() in [self.Columns.duration, self.Columns.notes]:
            obs = self.rows[model_index.row()]
            if model_index.column() == self.Columns.duration:
                obs.duration = value
            elif model_index.column() == self.Columns.notes:
                obs.comment = value
            self.observationUpdated.emit(obs)
            self.dataChanged.emit(model_index, model_index)
            return True
        return False

    def flags(self, model_index):
        default_flags = (Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        return (default_flags | Qt.ItemIsEditable) \
            if model_index.column() in [self.Columns.duration, self.Columns.notes] \
            else default_flags

    def insertRows(self, start, count, new_rows=None, *args, **kwargs):
        self.beginInsertRows(self.index(start, 0), start, start + count - 1)
        self.rows = self.rows[start:] + new_rows + self.rows[:start]
        self.rows.sort(key=lambda x: -1. * x.to_columns()[self.Columns.time])
        self.endInsertRows()
        return True

    def removeRows(self, start, count, *args, **kwargs):
        self.beginRemoveRows(self.index(start, 0), start, start + count - 1)
        del self.rows[start:(start + count)]
        self.endRemoveRows()
        return True

    def append_row(self, row):
        self.insertRows(self.rowCount(), 1, new_rows=[row])

    def remove_row(self, row):
        self.removeRows(row, 1)

    def empty(self):
        self.removeRows(0, self.rowCount())


class ObservationTableCell(QStyledItemDelegate):
    disabled_color = None
    Columns = ObservationTableModel.Columns

    def __init__(self, parent):
        super(QStyledItemDelegate, self).__init__(parent)
        self.disabled_color = QColor(Qt.lightGray)
        self.disabled_color.setAlphaF(0.5)

    def paint(self, painter, style, model_index):
        row, col = model_index.row(), model_index.column()
        # disabled look for organism column for Of Interest
        if col == self.Columns.organism and self.parent().item(row, self.Columns.type) == 'I':
            painter.save()
            painter.fillRect(style.rect, self.disabled_color)
            painter.restore()
        else:
            super().paint(painter, style, model_index)


class ObservationTable(QTableView):
    source_model = None
    Columns = ObservationTableModel.Columns

    # signals
    observationRowDeleted = pyqtSignal(Observation)
    durationClicked = pyqtSignal(Observation)
    goToObservation = pyqtSignal(Observation)
    observationUpdated = pyqtSignal(Observation)
    cellClicked = pyqtSignal(int, int)  # emit manually (previously auto)

    def set_data(self):
        # set model
        self.source_model = ObservationTableModel()
        self.setModel(self.source_model)
        # set columns
        self.setColumnHidden(self.Columns.id, True)  # TODO leave on for debug mode?
        self.setColumnHidden(self.Columns.type, True)  # TODO leave on for debug mode?
        self.setColumnWidth(self.Columns.organism, 250)
        self.setColumnHidden(self.Columns.duration, not GlobalFinPrintServer().is_lead())
        self.setColumnWidth(self.Columns.notes, 600)  # TODO make this width dynamic?
        # set rows
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.verticalHeader().setVisible(False)
        # set cells
        self.setItemDelegate(ObservationTableCell(self))
        # set events
        self.source_model.observationUpdated.connect(self.on_observation_updated)
        # show widget
        self.show()

    def on_observation_updated(self, obs):
        self.observationUpdated.emit(obs)

    def get_observation(self, row):
        return self.source_model.rows[row]

    def mousePressEvent(self, evt):
        old_index = self.currentIndex()
        index = self.indexAt(evt.pos())
        self.setCurrentIndex(index)
        if index.column() in [self.Columns.duration, self.Columns.notes] and old_index == index:
            self.edit(index)
        self.cellClicked.emit(index.row(), index.column())

    def item(self, row, col):
        return self.source_model.index(row, col).data()

    def add_row(self, obs):
        self.source_model.append_row(obs)

    def remove_row(self, row):
        self.clearSelection()
        self.source_model.remove_row(row)
        self.observationRowDeleted.emit(self.get_observation(row))

    def empty(self):
        if self.source_model is not None:
            self.source_model.empty()

    def customContextMenu(self, pos):
        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        set_duration_action = menu.addAction("Set Duration") if GlobalFinPrintServer().is_lead() else None
        go_to_observation_action = menu.addAction("Go To Observation")
        row = self.indexAt(pos).row()
        if row >= 0:
            action = menu.exec_(self.mapToGlobal(pos))
            if action == delete_action:
                self.remove_row(row)
            elif set_duration_action and action == set_duration_action:
                self.durationClicked.emit(self.get_observation(row))
            elif action == go_to_observation_action:
                self.goToObservation.emit(self.get_observation(row))


if __name__ == '__main__':
    app = QApplication(sys.argv)

    widget = CvVideoWidget()
    widget.setWindowTitle('PyQt - OpenCV Test')
    widget.show()

    sys.exit(app.exec_())
