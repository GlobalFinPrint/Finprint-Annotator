from global_finprint import Observation, GlobalFinPrintServer
from enum import IntEnum
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class ObservationTableModel(QAbstractTableModel):
    observationUpdated = pyqtSignal(Observation)

    class Columns(IntEnum):
        id = 0
        type = 1
        time = 2
        organism = 3
        duration = 4
        notes = 5

    class EventColumns(IntEnum):
        id = 0
        type = 1
        time = 2
        attributes = 3
        placeholder = 4
        notes = 5

    def __init__(self):
        self.rows = []
        self.columns = ['ID', 'Type', 'Time', 'Organism', 'Duration (ms)', 'Notes']
        self.event_columns = ['ID', 'Type', 'Time', 'Attributes', 'Placeholder', 'Notes']
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
        # self.rows.sort(key=lambda x: -1. * x.to_columns()[self.Columns.time])  # TODO solve sorting
        self.endInsertRows()
        return True

    def removeRows(self, start, count, *args, **kwargs):
        self.beginRemoveRows(self.index(start, 0), start, start + count - 1)
        del self.rows[start:(start + count)]
        self.endRemoveRows()
        return True

    def append_row(self, row):
        self.insertRows(self.rowCount(), 1 + len(row.events), new_rows=[row] + row.events)

    def remove_row(self, row):
        self.removeRows(row, 1 + len(row.events))

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
