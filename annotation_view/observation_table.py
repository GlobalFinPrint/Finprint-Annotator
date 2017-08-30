from global_finprint import Event, Observation, GlobalFinPrintServer
from enum import IntEnum
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from video_player import DialogActions
from annotation_view.util import ObservationColumn
from win32api import GetSystemMetrics

MARK_ZERO_TIME_ID = 16

class ObservationTableModel(QAbstractTableModel):
    observationUpdated = pyqtSignal(Observation)
    eventUpdated = pyqtSignal(Event)

    class Columns(IntEnum):
        event_time = 0
        id = 1
        type = 2
        annotator = 3
        organism = 4
        attributes = 5
        max_n = 6
        observation_comment = 7
        duration = 8
        frame_capture = 9
        event_notes = 10


    def __init__(self):
        self.rows = []
        self.columns = ObservationColumn.return_observation_table_coloumn_details()
        self.editable_columns = []
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
            if role == Qt.TextAlignmentRole :
                return Qt.AlignVCenter

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

    def get_coulmn_details(self):
        return self.columns

    def get_rows_details(self):
        return self.rows


class ObservationTableCell(QStyledItemDelegate):
    disabled_color = None
    obs_dupe_color = None
    Columns = ObservationTableModel.Columns
    observation_columns = [
        Columns.organism,
        Columns.observation_comment,
        Columns.duration
    ]

    def __init__(self, parent):
        super(QStyledItemDelegate, self).__init__(parent)
        self.disabled_color = QColor(Qt.lightGray)
        self.disabled_color.setAlphaF(0.5)
        self.obs_dupe_color = QColor(Qt.white)

    def drawBorder(self, painter, rect, no_top, column_id = False, row_number = False):
        pen1 = QPen(QColor('white'), 5, Qt.SolidLine)
        painter.setPen(pen1)
        if not no_top :
            painter.drawLine(rect.topLeft(), rect.topRight())

        if row_number == 0 :
           painter.drawLine(rect.topLeft(), rect.topRight())

        if column_id == 0: #space after first coloumn of each row
            painter.drawLine(rect.topLeft(), rect.bottomLeft())

        elif column_id == 10: #space after last coloumn of each row
            painter.drawLine(rect.topRight(), rect.bottomRight())

        pen = QPen(QColor('white'), 2, Qt.SolidLine)
        painter.setPen(pen)

        painter.drawLine(rect.topLeft(), rect.bottomLeft())



    def paint(self, painter, style, model_index):
        row, col = model_index.row(), model_index.column()
        event = self.parent().get_event(row)
        # disabled color for of interest
        if col == self.Columns.organism and self.parent().item(row, self.Columns.type) == 'I':
            painter.save()
            painter.fillRect(style.rect, self.disabled_color)
            self.drawBorder(painter, style.rect, col in self.observation_columns and not hasattr(event, 'first_flag'), col, row)
            painter.restore()

        # zebra striping table by observation
        else:
            painter.save()
            painter.fillRect(style.rect, event.obs_color)
            self.drawBorder(painter, style.rect, col in self.observation_columns and not hasattr(event, 'first_flag'),  col, row)
            painter.restore()
            if col not in self.observation_columns or hasattr(event, 'first_flag'):
                super().paint(painter, style, model_index)

class ObservationTable(QTableView):
    source_model = None
    current_set = None
    Columns = ObservationTableModel.Columns

    # signals
    durationClicked = pyqtSignal(Observation)
    goToEvent = pyqtSignal(Event)
    tableRefresh = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        stylesheet = """QTableView { gridline-color: #cccccc; border: 1px solid #cccccc;}
                        QHeaderView::section { height: 35px; background-color: rgb(131,140,158,51); color: rgb(41,86,109); padding-bottom:5px}
                        QScrollBar::vertical { border: 1px solid #999999; background:white; width:10px; margin: 0px 0px 0px 0px;}
                        QScrollBar::handle:vertical { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop: 0  rgb(131,140,158),
                            stop: 0.5 rgb(131,140,158),  stop:1 rgb(131,140,158)); min-height: 0px;}
                        QScrollBar::add-line:vertical { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop: 0  rgb(131,140,158),
                            stop: 0.5 rgb(131,140,158),  stop:1 rgb(131,140,158)); height: 0px; subcontrol-position: bottom; subcontrol-origin: margin;}
                        QScrollBar::sub-line:vertical { background: qlineargradient(x1:0, y1:0, x2:1, y2:0," stop: 0  rgb(131,140,158),
                            stop: 0.5 rgb(131,140,158),  stop:1 rgb(131,140,158)); height: 0px;subcontrol-position: top; subcontrol-origin:margin}
                        QScrollBar::horizontal { border: 1px solid #999999; background:white; height:10px; margin: 0px 0px 0px 0px;}
                        QScrollBar::handle:horizontal { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop: 0  rgb(131,140,158),
                            stop: 0.5 rgb(131,140,158),  stop:1 rgb(131,140,158)); min-width: 0px;}
                        QScrollBar::add-line:horizontal { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop: 0  rgb(131,140,158),
                            stop: 0.5 rgb(131,140,158),  stop:1 rgb(131,140,158)); width: 0px; subcontrol-position: right; subcontrol-origin: margin;}
                        QScrollBar::sub-line:horizontal { background: qlineargradient(x1:0, y1:0, x2:1, y2:0," stop: 0  rgb(131,140,158),
                            stop: 0.5 rgb(131,140,158),  stop:1 rgb(131,140,158)); width: 0px;subcontrol-position: left; subcontrol-origin:margin}
                            """

        self.setStyleSheet(stylesheet)
        self.setShowGrid(False)
        font = self.horizontalHeader().font()
        font.setPointSize(12)
        self.horizontalHeader().setFont(font)
        # multi key press event handling set
        self.keylist = set()
        self.firstrelease = None

    def set_data(self):
        # set model
        self.source_model = ObservationTableModel()
        self.setModel(self.source_model)
        self.windows_size = self.window().width()
        # set columns
        self.setColumnHidden(self.Columns.id, True)  # TODO leave on for debug mode?
        self.setColumnHidden(self.Columns.type, True)  # TODO leave on for debug mode?
        self.setColumnHidden(self.Columns.annotator, True)  # TODO leave on for debug mode?
        self.setColumnHidden(self.Columns.frame_capture, True)  # hide for now
        self.setColumnWidth(self.Columns.organism, 250)
        self.setColumnWidth(self.Columns.attributes, 250)
        self.setColumnWidth(self.Columns.observation_comment, (self.windows_size-250)/2)
        self.setColumnHidden(self.Columns.duration, not GlobalFinPrintServer().is_lead())
        self.setColumnWidth(self.Columns.event_notes, (self.windows_size-250)/2)
        # set rows
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.verticalHeader().setVisible(False)
        # set cells
        self.setItemDelegate(ObservationTableCell(self))
        # set events
        self.source_model.observationUpdated.connect(self.edit_observation)
        self.source_model.eventUpdated.connect(self.edit_event)

        self.setMinimumHeight(120)
        # show widget
        self.show()

    def get_event(self, row):
        return self.source_model.rows[row]

    def mousePressEvent(self, evt):
        old_index = self.currentIndex()
        index = self.indexAt(evt.pos())
        self.setCurrentIndex(index)
        if old_index == index:
         self.edit(index)

    def mouseDoubleClickEvent(self, *args, **kwargs):  # real signature unknown
        row = self.indexAt(args[0].pos()).row()
        self.video_context_menu({
            "action": DialogActions.edit_obs,
            "obs": self.get_event(row).observation,
            "column_number": self.indexAt(args[0].pos()).column(),
            "row_number": self.indexAt(args[0].pos()).row()},
        )

    def keyPressEvent(self, event):
        '''
        overriding system keyPressEvent to handle multikey press
        '''
        self.firstrelease = True
        self.keylist.add(event.key())

    def keyReleaseEvent(self, evt):
        '''
        overriding system keyReleaseEvent ,
        adds keyEvent in keyList when later key is
        released in case of multi key press
        '''
        if self.firstrelease == True:
            self.keylist.add(evt.key())
            self.process_multi_key_press()

        self.firstrelease = False
        if self.keylist:
            self.keylist.pop()

    def process_multi_key_press(self):
        '''
        MultiKey press handler Implementation
        '''
        aggregate_key_events = sum(self.keylist)
        if aggregate_key_events == Qt.Key_Control + Qt.Key_G:
           # selecting the row number and firing goToEvent
           self.goToEvent.emit(self.get_event(self.selectionModel().selectedRows()[0].row()))


    def item(self, row, col):
        return self.source_model.index(row, col).data()

    def add_row(self, row):
        self.source_model.append_row(row)

    def load_set(self, current_set):
        self.current_set = current_set
        self.refresh_model()

    def refresh_model(self):
        rotate_colors = [QColor(126, 211, 33, 128), QColor(126, 211, 33, 64)]
        rotate_index = 0
        # TODO note current row
        self.empty()
        obs = sorted(self.current_set.observations, key=lambda o: o.initial_time())
        row_space_list = []

        for o in obs:
            events = sorted(o.events, key=lambda e: e.event_time)
            events[-1].first_flag = True

            for e in events:
                e.obs_color = rotate_colors[rotate_index]
                self.add_row(e)
            rotate_index ^= 1
        self.resizeRowsToContents()
        self.tableRefresh.emit()
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
        #GLOB-568: If events in an observations is > 1 add delete_evet_action else delete_obs_action
        if row >= 0 and self.get_event(row) is not None and self.get_event(row).observation is not None:
            numbers_of_events = len(self.get_event(row).observation.events)
            if numbers_of_events > 1:
                delete_evt_action = delete_menu.addAction('This event within the observation')
            delete_obs_action = delete_menu.addAction('This entire observation')

        menu.addAction('Edit',lambda: self.edit_obs_action(pos))
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
            elif numbers_of_events > 1 and action == delete_evt_action:  # delete event
                evt = self.get_event(row)
                if self.confirm_delete_dialog(evt) :
                    self.remove_event(evt)
            elif action == delete_obs_action :  # delete observation
                obs = self.get_event(row).observation
                if self.confirm_delete_dialog(obs):
                    self.remove_observation(obs)
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

    def video_context_menu(self, optDict):
        print("observation table > video_context_menu")
        self.parent()._video_player.onMenuSelect(optDict)

    def edit_obs_action(self, pos):  # edit observation
        self.video_context_menu({
                "action": DialogActions.edit_obs,
                "obs": self.get_event(self.indexAt(pos).row()).observation,
                "column_number":self.indexAt(pos).column(),
                "row_number": self.indexAt(pos).row()},
        )

    def last_event_name(self):
        last_event_name = ''
        if self.current_set.observations is not None :
            last_event_name = self.current_set.observations[0].events[0]

        return last_event_name