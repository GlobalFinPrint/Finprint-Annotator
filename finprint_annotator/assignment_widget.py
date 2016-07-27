from pydispatch import dispatcher
from global_finprint import GlobalFinPrintServer
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class AssignmentWidget(QWidget):
    LEAD_COLUMNS = ['ID', 'Set/video name',
                    'Annotator',
                    'Date assigned', 'Status', 'Last activity']
    ANNO_COLUMNS = ['ID', 'Set/video name',
                    'Date assigned', 'Status', 'Last Activity']

    def __init__(self, sets):
        super().__init__()

        self._sets = sets
        self.is_lead = GlobalFinPrintServer().is_lead()
        self.layout = QVBoxLayout()

        # add filter dropdowns for lead
        if self.is_lead:
            filter_layout = QHBoxLayout()
            stylesheet = '''
            QComboBox {
                padding: 5px 10px;
            }
            QComboBox QAbstractItemView {
                padding: 3px;
            }
            '''
            trip_list = GlobalFinPrintServer().trip_list()
            self._trip_filter = QComboBox()
            self._trip_filter.setStyleSheet(stylesheet)
            self._trip_filter.setMaximumWidth(400)
            self._trip_filter.addItem('--- Filter by Trip ---')
            self._trip_filter.addItems(list(t['trip'] for t in trip_list['trips']))
            self._trip_filter.currentIndexChanged.connect(self._trip_filter_change)
            filter_layout.addWidget(self._trip_filter)

            self._set_filter = QComboBox()
            self._set_filter.setStyleSheet(stylesheet)
            self._set_filter.setMaximumWidth(400)
            self._set_filter.addItem('--- Filter by Set ---')
            self._set_filter.currentIndexChanged.connect(self._filter_change)
            filter_layout.addWidget(self._set_filter)

            anno_list = GlobalFinPrintServer().annotator_list()
            self._anno_filter = QComboBox()
            self._anno_filter.setStyleSheet(stylesheet)
            self._anno_filter.setMaximumWidth(400)
            self._anno_filter.addItem('--- Filter by Annotator ---')
            self._anno_filter.addItems(list(a['annotator'] for a in anno_list['annotators']))
            self._anno_filter.currentIndexChanged.connect(self._filter_change)
            filter_layout.addWidget(self._anno_filter)

            status_list = ['Not started', 'In progress', 'Ready for Review']
            self._status_filter = QComboBox()
            self._status_filter.setStyleSheet(stylesheet)
            self._status_filter.setMaximumWidth(400)
            self._status_filter.addItem('--- Filter by Status ---')
            self._status_filter.addItems(status_list)
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
        self.setMinimumSize(800, 400)
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
        self.set_table.horizontalHeader().setResizeMode(1, QHeaderView.Stretch)
        if self.is_lead:
            self.set_table.horizontalHeader().setResizeMode(2, QHeaderView.ResizeToContents)
        self.set_table.setColumnHidden(0, True)
        self.set_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.layout.addWidget(self.set_table)

        self.setLayout(self.layout)

        # add sets to table
        self.set_table.setRowCount(len(self._sets))
        for row, set in enumerate(self._sets):
            self._add_row(set, row)

        # make all items non editable
        for row in range(self.set_table.rowCount()):
            for col in range(self.set_table.columnCount()):
                item = self.set_table.item(row, col)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)

        # hook up click events
        self.set_table.cellDoubleClicked.connect(self._select_set)

    def _add_row(self, set, row):
        items = [
            QTableWidgetItem(str(set['id'])),
            QTableWidgetItem(set['set_code'])
        ]
        if self.is_lead:
            items += [QTableWidgetItem(set['assigned_to']['user'])]
        items += [
            QTableWidgetItem('TODO date assigned'),
            QTableWidgetItem('TODO status'),
            QTableWidgetItem('TODO last activity')
        ]
        for col, item in enumerate(items):
            self.set_table.setItem(row, col, item)

    def _select_set(self, row, _):
        set_id = int(self.set_table.item(row, 0).text())
        dispatcher.send('SET_SELECTED', dispatcher.Anonymous, value=set_id)

    def _trip_filter_change(self):
        # TODO update set dropdown
        self._filter_change()

    def _filter_change(self):
        # TODO update set list table
        pass
