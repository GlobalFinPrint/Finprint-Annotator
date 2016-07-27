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

        # TODO add filter dropdowns for lead

        # blue table header
        header = QLabel()
        header.setStyleSheet('background-color: rgb(41, 86, 109);color: rgb(255, 255, 255);font: 75 18pt "Arial";')
        header.setText('   Assignments' if self.is_lead else '   Assigned set list')
        header.setMinimumHeight(40)
        self.layout.addWidget(header)

        # set table
        self.set_table = QTableWidget(self)
        self.setMinimumSize(800, 400)
        stylesheet = '''
            QHeaderView::section { height: 35px; background-color: rgb(131,140,158,51); color: rgb(41,86,109); padding-bottom:5px}
        '''
        if not self.is_lead:  # TODO do we really want visual divergence on non-lead?
            self.set_table.setShowGrid(False)
            stylesheet += 'QTableView::item { border-bottom: 1px solid #cccccc; } '
        columns = self.LEAD_COLUMNS if self.is_lead else self.ANNO_COLUMNS
        self.set_table.setColumnCount(len(columns))
        self.set_table.setHorizontalHeaderLabels(columns)
        self.set_table.horizontalHeader().setResizeMode(1, QHeaderView.Stretch)
        if self.is_lead:
            self.set_table.horizontalHeader().setResizeMode(2, QHeaderView.ResizeToContents)
        self.set_table.setColumnHidden(0, True)
        self.set_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.set_table.setStyleSheet(stylesheet)
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
