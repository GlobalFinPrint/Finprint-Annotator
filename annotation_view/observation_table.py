from global_finprint import Event, Observation, GlobalFinPrintServer
from enum import IntEnum
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class ObservationTableModel(QAbstractTableModel):
    observationUpdated = pyqtSignal(Observation)
    eventUpdated = pyqtSignal(Event)

    class Columns(IntEnum):
        id = 0
        type = 1
        annotator = 2
        organism = 3
        observation_comment = 4
        duration = 5
        frame_capture = 6
        event_time = 7
        event_notes = 8
        attributes = 9

    def __init__(self):
        self.rows = []
        self.columns = ['ID',
                        'Type',
                        'Annotator',
                        'Organism',
                        'Observation Comment',
                        'Duration (ms)',
                        'Frame capture',
                        'Event time (ms)',
                        'Event notes',
                        'Attributes']
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
        return self.rows[model_index.row()].to_table_columns()[model_index.column()] \
            if role in [Qt.DisplayRole, Qt.EditRole] \
            else None

    def setData(self, model_index, value, role=None):
        if role == Qt.EditRole and model_index.column() in [self.Columns.duration, self.Columns.event_notes]:
            evt = self.rows[model_index.row()]
            if model_index.column() == self.Columns.duration:
                evt.observation.duration = value
                self.observationUpdated.emit(evt.observation)
            elif model_index.column() == self.Columns.observation_comment:
                evt.observation.comment = value
                self.observationUpdated.emit(evt.observation)
            elif model_index.column() == self.Columns.event_notes:
                evt.notes = value
                self.eventUpdated.emit(evt)
            self.dataChanged.emit(model_index, model_index)
            return True
        return False

    def flags(self, model_index):
        default_flags = (Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        return (default_flags | Qt.ItemIsEditable) \
            if model_index.column() in [self.Columns.duration, self.Columns.event_notes] \
            else default_flags

    def insertRows(self, start, count, new_rows=None, *args, **kwargs):
        self.beginInsertRows(self.index(start, 0), start, start + count - 1)
        self.rows = self.rows[start:] + new_rows + self.rows[:start]
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
    current_set = None
    Columns = ObservationTableModel.Columns

    # signals
    durationClicked = pyqtSignal(Observation)
    goToEvent = pyqtSignal(Event)
    observationUpdated = pyqtSignal(Observation)
    eventUpdated = pyqtSignal(Event)
    cellClicked = pyqtSignal(int, int)  # emit manually (previously auto)

    def set_data(self):
        # set model
        self.source_model = ObservationTableModel()
        self.setModel(self.source_model)
        # set columns
        self.setColumnHidden(self.Columns.id, True)  # TODO leave on for debug mode?
        self.setColumnHidden(self.Columns.type, True)  # TODO leave on for debug mode?
        self.setColumnHidden(self.Columns.annotator, True)  # TODO leave on for debug mode?
        self.setColumnHidden(self.Columns.frame_capture, True)  # TODO verify we want on/off
        self.setColumnWidth(self.Columns.organism, 250)
        self.setColumnWidth(self.Columns.observation_comment, 600)  # TODO make this width dynamic?
        self.setColumnHidden(self.Columns.duration, not GlobalFinPrintServer().is_lead())
        self.setColumnWidth(self.Columns.event_notes, 600)  # TODO make this width dynamic?
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

    def on_event_updated(self, evt):
        self.eventUpdated.emit(evt)

    def get_event(self, row):
        return self.source_model.rows[row]

    def mousePressEvent(self, evt):
        old_index = self.currentIndex()
        index = self.indexAt(evt.pos())
        self.setCurrentIndex(index)
        if index.column() in [self.Columns.duration, self.Columns.event_notes] and old_index == index:
            self.edit(index)
        self.cellClicked.emit(index.row(), index.column())

    def item(self, row, col):
        return self.source_model.index(row, col).data()

    def add_row(self, row):
        self.source_model.append_row(row)

    def load_set(self, current_set):
        self.current_set = current_set
        self.refresh_model()

    def update_obs(self, observations):
        self.current_set.observations = observations
        self.refresh_model()

    def refresh_model(self):
        self.empty()
        for o in self.current_set.observations:
            for e in o.events:
                self.add_row(e)
        self.resizeRowsToContents()

    def remove_event(self, evt):
        self.clearSelection()
        # TODO busy cursor
        self.current_set.delete_event(evt)
        self.refresh_model()

    def remove_observation(self, obs):
        self.clearSelection()
        # TODO busy cursor
        self.current_set.delete_observation(obs)
        self.refresh_model()

    def empty(self):
        if self.source_model is not None:
            self.source_model.empty()

    def customContextMenu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet('QMenu::item:selected { background-color: lightblue; }')
        delete_menu = menu.addMenu("Delete")
        delete_evt_action = delete_menu.addAction('Event')
        delete_obs_action = delete_menu.addAction('Entire observation')
        set_duration_action = menu.addAction("Set Duration") if GlobalFinPrintServer().is_lead() else None
        go_to_observation_action = menu.addAction("Go To Event")
        row = self.indexAt(pos).row()
        if row >= 0:
            action = menu.exec_(self.mapToGlobal(pos))
            if action == delete_evt_action:
                evt = self.get_event(row)
                if self.confirm_delete_dialog(evt):
                    self.remove_event(evt)
            elif action == delete_obs_action:
                obs = self.get_event(row).observation
                if self.confirm_delete_dialog(obs):
                    self.remove_observation(obs)
            elif set_duration_action and action == set_duration_action:
                self.durationClicked.emit(self.get_event(row).observation)
            elif action == go_to_observation_action:
                self.goToEvent.emit(self.get_event(row))

    def confirm_delete_dialog(self, obj):
        msg = 'Are you sure you want to delete {0}?'.format(str(obj))
        reply = QMessageBox.question(self, 'Delete confirmation', msg, QMessageBox.Yes, QMessageBox.No)
        return reply == QMessageBox.Yes
