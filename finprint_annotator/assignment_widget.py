from pydispatch import dispatcher
from global_finprint import GlobalFinPrintServer
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from annotation_view import convert_position, VideoLayoutWidget
from finprint_annotator.assignment_util import AssignmentFilter
import ast as ast

class AssignmentWidget(QWidget):
    LEAD_COLUMNS = ['ID', 'Set/video name',
                    'Annotator',
                    'Date assigned', 'Status', 'Last activity', 'Filename']
    ANNO_COLUMNS = ['ID', 'Set/video name',
                    'Date assigned', 'Status', 'Last Activity', 'Filename']
    def __init__(self, sets, assigned=False, assignment_filter = None, assignedByMe=0,):
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
            # Filter By trip Dropdown
            self.trip_list = GlobalFinPrintServer().trip_list()['trips']
            self._trip_filter = QComboBox()
            self._trip_filter.setStyleSheet(stylesheet)
            self._trip_filter.setMaximumWidth(400)
            self._trip_filter.addItem('--- Filter by Trip ---')
            for t in self.trip_list:
                self._trip_filter.addItem(t['trip'], t['id'])
            filter_layout.addWidget(self._trip_filter)

            # Custom font for header row in set name filter
            headerRowfont = QFont("Times", 9, QFont.Bold)
            self._set_filter = QComboBox()
            self._set_filter.setStyleSheet(stylesheet)
            self._set_filter.setMaximumWidth(400)
            self._set_filter.addItem('--- Filter by Set ---')
            for t in self.trip_list:
                # Add trip name header
                self._set_filter.addItem(t['trip'])
                # Disable trip name header row
                self._set_filter.model().item(len(self._set_filter)-1).setEnabled(False)
                # set custom font to header to have it look differently
                self._set_filter.model().item(len(self._set_filter) - 1).setFont(headerRowfont)
                for sn in t['sets']:
                    # Add set names
                    self._set_filter.addItem(sn['set'], sn['id'])

            filter_layout.addWidget(self._set_filter)

            # Filter By Annotator Dropdown

            anno_list = GlobalFinPrintServer().annotator_list()['annotators']
            self._anno_filter = QComboBox()
            self._anno_filter.setStyleSheet(stylesheet)
            self._anno_filter.setMaximumWidth(400)
            self._anno_filter.addItem('--- Filter by Annotator ---')
            for a in anno_list:
                self._anno_filter.addItem(a['annotator'], a['id'])

            filter_layout.addWidget(self._anno_filter)

            # Filter By Status Dropdown
            status_list = [(1, 'Not started'), (2, 'In progress'), (3, 'Ready for Review')]
            self._status_filter = QComboBox()
            self._status_filter.setStyleSheet(stylesheet)
            self._status_filter.setMaximumWidth(400)
            self._status_filter.addItem('--- Filter by Status ---')
            for s in status_list:
                self._status_filter.addItem(s[1], s[0])

            filter_layout.addWidget(self._status_filter)

            #addition for GLOB-535
            #affiliation_list = [(3, 'AIMS'), (6, 'Curtin University'),(2, 'FIU'),(1, 'Global Finprint'),
            #(5, 'JCU'),(0, 'No affiliation'),(4, 'SBU')]
            affiliation_list = GlobalFinPrintServer().affiliation_list()
            self._affiliation_filter = QComboBox()
            self._affiliation_filter.setStyleSheet(stylesheet)
            self._affiliation_filter.setMaximumWidth(400)
            self._affiliation_filter.addItem('--- Affiliation ---')
            for key,value in ast.literal_eval(affiliation_list.text).items():
                self._affiliation_filter.addItem(value,key)

            filter_layout.addWidget(self._affiliation_filter)
            filter_layout.addSpacing(10)
            styleSheetForCheckbox ='''
                    QCheckBox::indicator
                    {
                        width: 20px;
                        height: 20px;
                    }'''

            self._another_filter_layout = QHBoxLayout();

            self._limit_search = QCheckBox()
            self._limit_search.setStyleSheet(styleSheetForCheckbox)
            self._limit_search.setText("Limit to assignments made by me")
            self._limit_search.setCheckState(assignedByMe)

            self._another_filter_layout.addWidget(self._limit_search);

            self.resetSearch = QPushButton("Reset")
            self.resetSearch.setMaximumWidth(100)
            self.searchWithAllFilters = QPushButton("Search")
            self.searchWithAllFilters.setMaximumWidth(100)

            self.searchWithAllFilters.clicked.connect(self._filter_change)
            self.resetSearch.clicked.connect(self._clear_filter)
            self._another_filter_layout.addSpacing(400)
            self._another_filter_layout.addWidget(self.resetSearch);
            self._another_filter_layout.addWidget(self.searchWithAllFilters);
            filter_layout.addStretch(1)

            self.layout.addLayout(filter_layout)
            self.layout.addSpacing(20)
            self.layout.addLayout(self._another_filter_layout)

        # blue table header
        self.headerLabel = QLabel()
        self.headerLabel.setStyleSheet('''
            padding-left: 10px;
            background-color: rgb(41, 86, 109);
            color: rgb(255, 255, 255);
            font: 75 18pt "Arial";
        ''')
        self.headerLabel.setMinimumHeight(40)
        self.layout.addWidget(self.headerLabel)

        # set table
        self.set_table = QTableWidget(self)
        #increasing size of widget GLOB-525
        self.setMinimumSize(1200, 800)

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
        for col in range(2, self.set_table.columnCount() - 2):
            self.set_table.horizontalHeader().setResizeMode(col, QHeaderView.ResizeToContents)

        # hide ID and filename columns
        self.set_table.setColumnHidden(0, True)
        self.set_table.setColumnHidden(self.set_table.columnCount() - 1, True)

        self.layout.addWidget(self.set_table)
        self.setLayout(self.layout)

        if self.is_lead and not assigned:
          # GLOB-544: retain filter status
          self._prev_state_assignment_filter = assignment_filter

          if self._prev_state_assignment_filter:
             self.set_prev_state_of_filters()
          else:
            # assignement the intial value which is achieved after reset or default
             self._prev_state_assignment_filter = AssignmentFilter()

        # populate table with current sets
        self._populate_table()

        # hook up click events
        self.set_table.cellDoubleClicked.connect(self._select_set)

    def _populate_table(self):
        # clear any current rows
        for row in range(self.set_table.rowCount()):
            self.set_table.removeRow(row)

        # Change the header label counter
        headerText = 'Assignments' if self.is_lead else 'Assigned set list'
        # Adding no. of assignments to the header label for quickly knowing the count
        self.headerLabel.setText(headerText + ' (' + str(len(self._sets)) + ')')

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
            if set['file'] == 'None' or set['file'] == '' or set['file'] is None:
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
        if self._affiliation_filter.currentIndex() >= 0:
            params['affiliation_id'] = self._affiliation_filter.itemData(self._affiliation_filter.currentIndex())
        if  self._limit_search.isChecked() :
            params['assigned_by_me'] = True

        self._sets = GlobalFinPrintServer().set_list(**params)['sets']
        self._populate_table()
        self.retain_filter_status()


    def _clear_filter(self):
        self._trip_filter.setCurrentIndex(0)
        self._set_filter.setCurrentIndex(0)
        self._anno_filter.setCurrentIndex(0)
        self._status_filter.setCurrentIndex(0)
        self._affiliation_filter.setCurrentIndex(0)
        self._limit_search.setCheckState(2)
        self._prev_state_assignment_filter.setFilterValues()


    def retain_filter_status(self):
        if self._limit_search.isChecked() :
            limit_search_index =2
        else:
            limit_search_index = 0

        self._prev_state_assignment_filter.setFilterValues(
        self._trip_filter.currentIndex(),
        self._set_filter.currentIndex(),
        self._anno_filter.currentIndex(),
        self._status_filter.currentIndex(),
        self._affiliation_filter.currentIndex(), limit_search_index)


    def set_prev_state_of_filters(self):
        self._trip_filter.setCurrentIndex(self._prev_state_assignment_filter._trip_filter_index)
        self._set_filter.setCurrentIndex(self._prev_state_assignment_filter._set_filter_index)
        self._anno_filter.setCurrentIndex(self._prev_state_assignment_filter._anno_filter_index)
        self._status_filter.setCurrentIndex(self._prev_state_assignment_filter._status_filter_index)
        self._affiliation_filter.setCurrentIndex(self._prev_state_assignment_filter._affiliation_filter_index)
        self._limit_search.setCheckState(self._prev_state_assignment_filter._limit_search_index)
        self._filter_change()


