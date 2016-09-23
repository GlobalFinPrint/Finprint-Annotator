from pydispatch import dispatcher
from global_finprint import GlobalFinPrintServer
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from annotation_view import convert_position, VideoLayoutWidget


class AssignmentWidget(QWidget):
    LEAD_COLUMNS = ['ID', 'Set/video name',
                    'Annotator',
                    'Date assigned', 'Status', 'Last activity', 'Filename']
    ANNO_COLUMNS = ['ID', 'Set/video name',
                    'Date assigned', 'Status', 'Last Activity', 'Filename']

    def __init__(self, sets, assigned=False):
        super().__init__()

        self._sets = sets
        self.is_lead = GlobalFinPrintServer().is_lead()
        self.layout = QVBoxLayout()

        # add filter dropdowns for lead
        if self.is_lead and not assigned:
            filter_layout = QHBoxLayout()
            stylesheet = '''
            QComboBox {
                padding: 5px 10px;
            }
            QComboBox QAbstractItemView {
                padding: 3px;
            }
            '''
            self.trip_list = GlobalFinPrintServer().trip_list()['trips']
            self._trip_filter = QComboBox()
            self._trip_filter.setStyleSheet(stylesheet)
            self._trip_filter.setMaximumWidth(400)
            self._trip_filter.addItem('--- Filter by Trip ---')
            for t in self.trip_list:
                self._trip_filter.addItem(t['trip'], t['id'])
            self._trip_filter.currentIndexChanged.connect(self._trip_filter_change)
            filter_layout.addWidget(self._trip_filter)

            self._set_filter = QComboBox()
            self._set_filter.setStyleSheet(stylesheet)
            self._set_filter.setMaximumWidth(400)
            self._set_filter.addItem('--- Filter by Set ---')
            self._set_filter.currentIndexChanged.connect(self._filter_change)
            filter_layout.addWidget(self._set_filter)

            anno_list = GlobalFinPrintServer().annotator_list()['annotators']
            self._anno_filter = QComboBox()
            self._anno_filter.setStyleSheet(stylesheet)
            self._anno_filter.setMaximumWidth(400)
            self._anno_filter.addItem('--- Filter by Annotator ---')
            for a in anno_list:
                self._anno_filter.addItem(a['annotator'], a['id'])
            self._anno_filter.currentIndexChanged.connect(self._filter_change)
            filter_layout.addWidget(self._anno_filter)

            status_list = [(1, 'Not started'), (2, 'In progress'), (3, 'Ready for Review')]
            self._status_filter = QComboBox()
            self._status_filter.setStyleSheet(stylesheet)
            self._status_filter.setMaximumWidth(400)
            self._status_filter.addItem('--- Filter by Status ---')
            for s in status_list:
                self._status_filter.addItem(s[1], s[0])
            self._status_filter.currentIndexChanged.connect(self._filter_change)
            filter_layout.addWidget(self._status_filter)

            filter_layout.addStretch(1)
            self.layout.addLayout(filter_layout)

        # blue table header
        header = QLabel()
        header.setStyleSheet('''
            padding-left: 10px;
            background-color: rgb(41, 86, 109);
            color: rgb(255, 255, 255);
            font: 75 18pt "Arial";
        ''')
        header.setText('Assignments' if self.is_lead else 'Assigned set list')
        header.setMinimumHeight(40)
        self.layout.addWidget(header)

        # set table
        self.set_table = QTableWidget(self)
        self.setMinimumSize(900, 400)
        self.set_table.setStyleSheet('''
            QHeaderView::section {
                height: 35px;
                background-color: rgb(131,140,158,51);
                color: rgb(41,86,109);
                padding-bottom:5px
            }
        ''')
        columns = self.LEAD_COLUMNS if self.is_lead else self.ANNO_COLUMNS
        self.set_table.setColumnCount(len(columns))
        self.set_table.setHorizontalHeaderLabels(columns)
        self.set_table.setSelectionBehavior(QAbstractItemView.SelectRows)

        # first column takes up extra space then fit rest of columns
        self.set_table.horizontalHeader().setResizeMode(1, QHeaderView.Stretch)
        for col in range(2, self.set_table.columnCount()):
            self.set_table.horizontalHeader().setResizeMode(col, QHeaderView.ResizeToContents)

        # hide ID and filename columns
        self.set_table.setColumnHidden(0, True)
        self.set_table.setColumnHidden(self.set_table.columnCount() - 1, True)

        self.layout.addWidget(self.set_table)
        self.setLayout(self.layout)

        # populate table with current sets
        self._populate_table()

        # hook up click events
        self.set_table.cellDoubleClicked.connect(self._select_set)

    def _populate_table(self):
        # clear any current rows
        for row in range(self.set_table.rowCount()):
            self.set_table.removeRow(row)

        # add sets to table
        self.set_table.setRowCount(len(self._sets))
        for row, set in enumerate(self._sets):
            self._add_row(set, row)

    def _add_row(self, set, row):
        items = [
            QTableWidgetItem(str(set['id'])),
            QTableWidgetItem(set['set_code'])
        ]
        if self.is_lead:
            items += [QTableWidgetItem(set['assigned_to']['user'])]
        items += [
            QTableWidgetItem(set['assigned_at']),
            QTableWidgetItem(set['status']['name'] + ' ' + convert_position(set['progress'])),
            QTableWidgetItem(set['last_activity']),
            QTableWidgetItem(set['file']),
        ]
        for col, item in enumerate(items):
            if set['file'] == 'None':
                item.setTextColor(QColor(204, 204, 204))
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.set_table.setItem(row, col, item)

    def _select_set(self, row, _):
        filename = self.set_table.item(row, self.set_table.columnCount() - 1).text()
        set_id = int(self.set_table.item(row, 0).text())
        if filename == 'None':
            msgbox = QMessageBox()
            msgbox.setText('No video file has been specified for this set')
            msgbox.setWindowTitle('Missing video')
            msgbox.exec_()
        elif VideoLayoutWidget.get_local_file(filename) is False:
            msgbox = QMessageBox()
            msgbox.setText("Could not load file: {0}".format(filename))
            msgbox.setWindowTitle("Error Loading Video")
            msgbox.exec_()
        else:
            dispatcher.send('SET_SELECTED', dispatcher.Anonymous, value=set_id)

    def _trip_filter_change(self):
        self._set_filter.clear()
        self._set_filter.addItem('--- Filter by Set ---')
        selected_trip = next((t for t in self.trip_list if t['trip'] == self._trip_filter.currentText()), None)
        if selected_trip:
            for set in selected_trip['sets']:
                self._set_filter.addItem(set['set'], set['id'])
        self._filter_change()

    def _filter_change(self):
        params = {'filtered': True}
        if self._trip_filter.currentIndex() > 0:
            params['trip_id'] = self._trip_filter.itemData(self._trip_filter.currentIndex())
        if self._set_filter.currentIndex() > 0:
            params['set_id'] = self._set_filter.itemData(self._set_filter.currentIndex())
        if self._anno_filter.currentIndex() > 0:
            params['annotator_id'] = self._anno_filter.itemData(self._anno_filter.currentIndex())
        if self._status_filter.currentIndex() > 0:
            params['status_id'] = self._status_filter.itemData(self._status_filter.currentIndex())
        self._sets = GlobalFinPrintServer().set_list(**params)['sets']
        self._populate_table()
