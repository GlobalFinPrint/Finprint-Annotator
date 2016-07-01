from global_finprint import Event, Observation, GlobalFinPrintServer
from enum import IntEnum
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class ObservationTableModel(QAbstractTableModel):
    observationUpdated = pyqtSignal(Observation)
    eventUpdated = pyqtSignal(Event)

    class Columns(IntEnum):
        event_time = 0
        id = 1
        type = 2
        annotator = 3
        organism = 4
        observation_comment = 5
        duration = 6
        frame_capture = 7
        event_notes = 8
        attributes = 9

    def __init__(self):
        self.rows = []
        self.columns = ['Time',
                        'ID',
                        'Type',
                        'Annotator',
                        'Organism',
                        'Observation Comment',
                        'Duration (ms)',
                        'Frame capture',
                        'Event notes',
                        'Attributes']
        self.editable_columns = [
            self.Columns.observation_comment,
            self.Columns.duration,
            self.Columns.event_notes
        ]
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
        if len(self.rows) > 0 and role in [Qt.DisplayRole, Qt.EditRole]:
            row = self.rows[model_index.row()]
            columns = row.to_table_columns()
            return columns[model_index.column()]
        else:
            return None

    def setData(self, model_index, value, role=None):
        if role == Qt.EditRole and model_index.column() in self.editable_columns:
            evt = self.rows[model_index.row()]
            if model_index.column() == self.Columns.duration:
                evt.observation.duration = value
                self.observationUpdated.emit(evt.observation)
            elif model_index.column() == self.Columns.observation_comment:
                evt.observation.comment = value
                self.observationUpdated.emit(evt.observation)
            elif model_index.column() == self.Columns.event_notes:
                evt.note = value
                self.eventUpdated.emit(evt)
            self.dataChanged.emit(model_index, model_index)
            return True
        return False

    def flags(self, model_index):
        default_flags = (Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        return (default_flags | Qt.ItemIsEditable) \
            if model_index.column() in self.editable_columns \
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
        self.reset()


class ObservationTableCell(QStyledItemDelegate):
    disabled_color = None
    obs_dupe_color = None
    Columns = ObservationTableModel.Columns

    def __init__(self, parent):
        super(QStyledItemDelegate, self).__init__(parent)
        self.disabled_color = QColor(Qt.lightGray)
        self.disabled_color.setAlphaF(0.5)
        self.obs_dupe_color = QColor(Qt.white)

    def paint(self, painter, style, model_index):
        row, col = model_index.row(), model_index.column()
        event = self.parent().get_event(row)

        # disabled look for organism column for Of Interest
        if col == self.Columns.organism and self.parent().item(row, self.Columns.type) == 'I':
            painter.save()
            painter.fillRect(style.rect, self.disabled_color)
            painter.restore()

        # don't fill in observation values after the first row
        elif col in [self.Columns.organism, self.Columns.observation_comment, self.Columns.duration] \
                and sorted(event.observation.events, key=lambda e: e.event_time)[0].id != event.id:
            painter.save()
            painter.fillRect(style.rect, self.obs_dupe_color)
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        stylesheet = """QTableView { gridline-color #cccccc; border: 1px solid #cccccc;}
                        QHeaderView::section {  height: 30px; background-color: rgb(131,140,158,51); color: rgb(41,86,109,254); }"""
        self.setStyleSheet(stylesheet)
        font = self.horizontalHeader().font()
        font.setPointSize(12)
        self.horizontalHeader().setFont(font)

    def set_data(self):
        # set model
        self.source_model = ObservationTableModel()
        self.setModel(self.source_model)

        # set columns
        self.setColumnHidden(self.Columns.id, True)  # TODO leave on for debug mode?
        self.setColumnHidden(self.Columns.type, True)  # TODO leave on for debug mode?
        self.setColumnHidden(self.Columns.annotator, True)  # TODO leave on for debug mode?
        self.setColumnHidden(self.Columns.frame_capture, True)  # hide for now
        self.setColumnWidth(self.Columns.organism, 250)
        self.setColumnWidth(self.Columns.observation_comment, 600)
        self.setColumnHidden(self.Columns.duration, not GlobalFinPrintServer().is_lead())
        self.setColumnWidth(self.Columns.event_notes, 600)

        # set rows
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.verticalHeader().setVisible(False)

        # set cells
        self.setItemDelegate(ObservationTableCell(self))

        # set events
        self.source_model.observationUpdated.connect(self.edit_observation)
        self.source_model.eventUpdated.connect(self.edit_event)

        # show widget
        self.show()

    def get_event(self, row):
        return self.source_model.rows[row]

    def mousePressEvent(self, evt):
        old_index = self.currentIndex()
        index = self.indexAt(evt.pos())
        self.setCurrentIndex(index)
        if index.column() in self.source_model.editable_columns and old_index == index:
            self.edit(index)

    def item(self, row, col):
        return self.source_model.index(row, col).data()

    def add_row(self, row):
        self.source_model.append_row(row)

    def load_set(self, current_set):
        self.current_set = current_set
        self.refresh_model()

    def refresh_model(self):
        # TODO note current row
        self.empty()
        obs = sorted(self.current_set.observations, key=lambda o: o.initial_time(), reverse=True)
        for o in obs:
            events = sorted(o.events, key=lambda e: e.event_time, reverse=True)
            for e in events:
                self.add_row(e)
        self.resizeRowsToContents()
        # TODO return to noted row

    def edit_event(self, evt):
        values = evt.to_dict()
        values['attribute'] = [a['id'] for a in values['attribute'][:]]
        self.current_set.edit_event(evt, values)
        self.refresh_model()

    def edit_observation(self, obs):
        self.current_set.edit_observation(obs, obs.to_dict())
        self.refresh_model()

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
        row = self.indexAt(pos).row()

        menu = QMenu(self)
        menu.setStyleSheet('QMenu::item:selected { background-color: lightblue; }')
        delete_menu = menu.addMenu('Delete')
        delete_evt_action = delete_menu.addAction('Event')
        delete_obs_action = delete_menu.addAction('Observation')
        edit_menu = menu.addMenu('Edit')
        edit_evt_action = edit_menu.addAction('Event')
        edit_obs_action = edit_menu.addAction('Observation')
        set_duration_action = menu.addAction('Set Duration') if GlobalFinPrintServer().is_lead() else -1
        go_to_event_action = menu.addAction('Go To Event')
        if self.get_event(row).observation.type_choice == 'A':
            change_organism_menu = menu.addMenu('Change organism')
            grouping = {}
            for animal in self.current_set.animals:
                if animal.group not in grouping:
                    grouping[animal.group] = []
                grouping[animal.group].append(animal)
            for group in grouping.keys():
                group_menu = change_organism_menu.addMenu(group)
                for animal in grouping[group]:
                    act = group_menu.addAction(str(animal))
                    act.setData(animal)
        cancel_action = menu.addAction('Cancel')

        if row >= 0:
            action = menu.exec_(self.mapToGlobal(pos))
            if action is None or action == cancel_action:  # menu cancelled
                pass
            elif action == delete_evt_action:  # delete event
                evt = self.get_event(row)
                if self.confirm_delete_dialog(evt):
                    self.remove_event(evt)
            elif action == delete_obs_action:  # delete observation
                obs = self.get_event(row).observation
                if self.confirm_delete_dialog(obs):
                    self.remove_observation(obs)
            elif action == edit_evt_action:  # edit event
                self.video_context_menu().display_event_dialog(
                    action=self.video_context_menu().DialogActions.edit_event,
                    event=self.get_event(row)
                )
            elif action == edit_obs_action:  # edit observation
                self.video_context_menu().display_event_dialog(
                    action=self.video_context_menu().DialogActions.edit_obs,
                    obs=self.get_event(row).observation
                )
            elif set_duration_action and action == set_duration_action:  # set duration
                self.durationClicked.emit(self.get_event(row).observation)
            elif action == go_to_event_action:  # go to event
                self.goToEvent.emit(self.get_event(row))
            elif type(action.data()).__name__ == 'Animal':  # change organism
                obs = self.get_event(row).observation
                self.current_set.edit_observation(obs, {'animal_id': action.data().id})
                self.refresh_model()

    def confirm_delete_dialog(self, obj):
        msg = 'Are you sure you want to delete {0}?'.format(str(obj))
        reply = QMessageBox.question(self, 'Delete confirmation', msg, QMessageBox.Yes, QMessageBox.No)
        return reply == QMessageBox.Yes

    def video_context_menu(self):
        return self.parent()._video_player._context_menu
