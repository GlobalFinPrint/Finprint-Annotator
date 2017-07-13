from pydispatch import dispatcher
from global_finprint import GlobalFinPrintServer
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from annotation_view import convert_position, VideoLayoutWidget
from finprint_annotator.assignment_filter import AssignmentFilterDTO
import ast as ast

class AssignmentWidget(QWidget):
    LEAD_COLUMNS = ['ID', 'Set/video name',
                    'Annotator',
                    'Date assigned', 'Status', 'Last activity', 'Filename']
   # LEAD_COLUMNS = ['ID', 'Set/video name',
   #                 'Annotator', 'Project name',
    #                'Date assigned', 'Status', 'Last activity', 'Filename']
    ANNO_COLUMNS = ['ID', 'Set/video name',
                    'Date assigned', 'Status', 'Last Activity', 'Filename']
    #ANNO_COLUMNS = ['ID', 'Set/video name', 'Project name',
     #               'Date assigned', 'Status', 'Last Activity', 'Filename']
    def __init__(self, sets, assigned=False, assignedByMe=0,):
        super().__init__()

        self._sets = sets
        self.is_lead = GlobalFinPrintServer().is_lead()
        self.layout = QVBoxLayout()
        self._assignment_filter = AssignmentFilterDTO.get_instance()
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
            # Custom font for header row in set name filter
            self.headerRowfont = QFont("Times", 9, QFont.Bold)
            self._set_filter = QComboBox()
            self._set_filter.setStyleSheet(stylesheet)
            self._set_filter.setMaximumWidth(400)


            # Filter By trip Dropdown
            self.trip_list = GlobalFinPrintServer().trip_list()['trips']
            self._trip_filter = QComboBox()
            self._trip_filter.setStyleSheet(stylesheet)
            self._trip_filter.setMaximumWidth(400)
            self._trip_filter.addItem('--- Filter by Trip ---')

            for t in self.trip_list:
                self._trip_filter.addItem(t['trip'], t['id'])

            self._trip_filter.currentIndexChanged.connect(self.restrict_filter_based_on_trip_selected)
            filter_layout.addWidget(self._trip_filter)

            self._reef_filter = QComboBox()
            self._reef_filter.setStyleSheet(stylesheet)
            self._reef_filter.setMaximumWidth(400)
            self._reef_filter.addItem('--- Filter by Reef ---')
            self._reef_filter.currentIndexChanged.connect(self.restrict_filter_based_on_trip_reef_selected)
            # intialising values of set_filters
            filter_layout.addWidget(self._reef_filter)
            filter_layout.addWidget(self._set_filter)
            self.control_set_filter_based_on_trip_selected()

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
       # self.set_table.horizontalHeader().setResizeMode(1, QHeaderView.Stretch)
        for col in range(1, self.set_table.columnCount() - 1):
            self.set_table.horizontalHeader().setResizeMode(col, QHeaderView.ResizeToContents)
            self.set_table.horizontalHeader().setResizeMode(col, QHeaderView.Stretch)

        # hide ID and filename columns
        self.set_table.setColumnHidden(0, True)
        self.set_table.setColumnHidden(self.set_table.columnCount() - 1, True)

        self.layout.addWidget(self.set_table)
        self.setLayout(self.layout)

        if self.is_lead and not assigned:
          # GLOB-544: retain filter status
          if self._assignment_filter :
            self.set_prev_state_of_filters()

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
         #   QTableWidgetItem(set['project_name']),
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
        self.persist_filter_status()
        params = {'filtered': True}
        if self._trip_filter.currentIndex() > 0:
            params['trip_id'] = self._assignment_filter.get_trip_filter()["id"]
        if self._reef_filter.currentIndex() > 0:
            params['reef_id'] = self._assignment_filter.get_reef_filter()["id"]
        if self._set_filter.currentIndex() > 0:
            params['set_id'] = self._assignment_filter.get_set_filter()["id"]
        if self._anno_filter.currentIndex() > 0:
            params['annotator_id'] = self._assignment_filter.get_anno_filter()["id"]
        if self._status_filter.currentIndex() > 0:
            params['status_id'] = self._assignment_filter.get_status_filter()["id"]
        if self._affiliation_filter.currentIndex() > 0:
            params['affiliation_id'] = self._assignment_filter.get_affiliation_filter()["id"]
        if  self._assignment_filter.get_limit_search()["id"] == 2:
            params['assigned_by_me'] = True

        self._sets = GlobalFinPrintServer().set_list(**params)['sets']
        self._populate_table()



    def _clear_filter(self):
        self._trip_filter.setCurrentIndex(0)
        self._reef_filter.setCurrentIndex(0)
        self._set_filter.setCurrentIndex(0)
        self._anno_filter.setCurrentIndex(0)
        self._status_filter.setCurrentIndex(0)
        self._affiliation_filter.setCurrentIndex(0)
        self._limit_search.setCheckState(2)
        self._assignment_filter.setFilterValues()


    def persist_filter_status(self):
        ''' persisting data in ""AssignmentFilterVO"" data model for using
         when filter list button is pressed again in same user session'''
        if self._limit_search.isChecked() :
            _limit_search ={"id":2}
        else:
            _limit_search = {"id":0}

        if self._trip_filter.currentIndex() == 0 :
            _trip_filter = {"id": -1 ,"name": self._trip_filter.itemText(self._trip_filter.currentIndex())}
        else:
            _trip_filter = {"id": self._trip_filter.itemData(self._trip_filter.currentIndex()),
                            "name": self._trip_filter.itemText(self._trip_filter.currentIndex())}

        if self._reef_filter.currentIndex() == 0:
            _reef_filter = {"id": -1 ,"name": self._reef_filter.itemText(self._reef_filter.currentIndex())}
        else:
            _reef_filter = {"id": self._reef_filter.itemData(self._reef_filter.currentIndex()),
                           "name": self._reef_filter.itemText(self._reef_filter.currentIndex())}

        if self._set_filter.currentIndex() == 0:
            _set_filter = {"id": -1 ,"name": self._set_filter.itemText(self._set_filter.currentIndex())}
        else:
            _set_filter = {"id": self._set_filter.itemData(self._set_filter.currentIndex()),
                           "name": self._set_filter.itemText(self._set_filter.currentIndex())}

        if self._anno_filter.currentIndex() == 0:
            _anno_filter = {"id": -1 ,"name": self._anno_filter.itemText(self._anno_filter.currentIndex())}
        else:
            _anno_filter = {"id": self._anno_filter.itemData(self._anno_filter.currentIndex()),
                            "name": self._anno_filter.itemText(self._anno_filter.currentIndex())}

        if self._status_filter.currentIndex() == 0:
            _status_filter = {"id": -1 ,"name": self._status_filter.itemText(self._status_filter.currentIndex())}
        else :
            _status_filter = {"id": self._status_filter.itemData(self._status_filter.currentIndex()),
                              "name": self._status_filter.itemText(self._status_filter.currentIndex())}

        if self._affiliation_filter.currentIndex() == 0:
            _affiliation_filter = {"id": -1 ,"name": self._affiliation_filter.itemText(self._affiliation_filter.currentIndex())}
        else:
            _affiliation_filter = {"id": self._affiliation_filter.itemData(self._affiliation_filter.currentIndex()),
                                   "name": self._affiliation_filter.itemText(self._affiliation_filter.currentIndex())}


        self._assignment_filter.setFilterValues( _trip_filter, _reef_filter,  _set_filter, _anno_filter,
                                                 _status_filter,_affiliation_filter, _limit_search)


    def set_prev_state_of_filters(self):
        self._trip_filter.setCurrentIndex( self.returnZeroIndexIfFilterIsNotApplied(
            self._trip_filter.findData(self._assignment_filter.get_trip_filter()["id"])))
        self._reef_filter.setCurrentIndex(self.returnZeroIndexIfFilterIsNotApplied(
            self._reef_filter.findData(self._assignment_filter.get_reef_filter()["id"])))
        self._set_filter.setCurrentIndex( self.returnZeroIndexIfFilterIsNotApplied(
                self._set_filter.findData( self._assignment_filter.get_set_filter()["id"])))
        self._anno_filter.setCurrentIndex(self.returnZeroIndexIfFilterIsNotApplied(
            self._anno_filter.findData(self._assignment_filter.get_anno_filter()["id"])))
        self._status_filter.setCurrentIndex(self.returnZeroIndexIfFilterIsNotApplied(
            self._status_filter.findData(self._assignment_filter.get_status_filter()["id"])))
        self._affiliation_filter.setCurrentIndex(self.returnZeroIndexIfFilterIsNotApplied(
            self._affiliation_filter.findData(self._assignment_filter.get_affiliation_filter()["id"])))
        self._limit_search.setCheckState(self._assignment_filter.get_limit_search()["id"])
        self._filter_change()
        # adding for dynamic changes to restrict
       # self.restrict_filter_based_on_trip_reef_selected()

    def restrict_filter_based_on_trip_selected(self):
        self.control_set_filter_based_on_trip_selected()

    def restrict_filter_based_on_trip_reef_selected(self):
        reef_id = None
        trip_id = None
        if self._trip_filter.currentIndex() > 0:
            trip_id = self._trip_filter.itemData(self._trip_filter.currentIndex())
        if self._reef_filter.currentIndex() > 0:
            reef_id = self._reef_filter.itemData(self._reef_filter.currentIndex())

        reef_set_list = GlobalFinPrintServer().reef_set_list(trip_id, reef_id)
        self.filter_group_by_set_reef(reef_set_list)

    def control_set_filter_based_on_trip_selected(self):
            ''''filtering sets if a trip is selected'''
            reef_id = None
            trip_id = None
            if self._trip_filter.currentIndex() > 0:
                trip_id = self._trip_filter.itemData(self._trip_filter.currentIndex())

            reef_set_list = GlobalFinPrintServer().reef_set_list(trip_id, reef_id)
            self.filter_group_by_set_reef(reef_set_list)

    def returnZeroIndexIfFilterIsNotApplied(self,filterIndex):
        if filterIndex == -1 :
            return 0
        else :
           return filterIndex

    def filter_group_by_set_reef(self, reef_set_list):
       _reef_grouping = {}
       _sets_grouping = {}
       sets_dic =  reef_set_list['sets']
       reefs_dic = None
       if 'reefs' in reef_set_list :
           reefs_dic = reef_set_list['reefs']

       if sets_dic :
           for set_data in sets_dic:
               if set_data['group'] not in _sets_grouping :
                   _list = []
                   _list.append(set_data)
                   _sets_grouping[set_data['group']] = _list
               else :
                   _list1 = _sets_grouping.get(set_data['group'])
                   _list1.append(set_data)
                   _sets_grouping[set_data['group']] = _list1

       if reefs_dic:
            for reef_data in reef_set_list['reefs'] :
                 if reef_data['reef_group'] not in _reef_grouping:
                     _list_reef = []
                     _list_reef.append(reef_data)
                     _reef_grouping[reef_data['reef_group']]= _list_reef
                 else:
                     _list1_reef = _reef_grouping.get(reef_data['reef_group'])
                     _list1_reef.append(reef_data)
                     _reef_grouping[reef_data['reef_group']] = _list1_reef

       self.refill_set_reef_filter(_reef_grouping, _sets_grouping)


    def refill_set_reef_filter(self, _reef_grouping=None, _sets_grouping=None):
        if _sets_grouping!= None :
            self._set_filter.blockSignals(True)
            self._set_filter.clear()
            self._set_filter.addItem('--- Filter by Set ---')
            self._set_filter.setCurrentIndex(0)
            for key in _sets_grouping :
                self._set_filter.addItem(key)
                # Disable trip name header row
                self._set_filter.model().item(len(self._set_filter) - 1).setEnabled(False)
                # set custom font to header to have it look differently
                self._set_filter.model().item(len(self._set_filter) - 1).setFont(self.headerRowfont)
                for each_set in _sets_grouping[key] :
                   self._set_filter.addItem(each_set['code'], each_set['id'])

            self._set_filter.blockSignals(False)

        if _reef_grouping :
            self._reef_filter.blockSignals(True)
            self._reef_filter.clear()
            self._reef_filter.addItem('--- Filter by Reef ---')
            self._reef_filter.setCurrentIndex(0)
            for key in _reef_grouping:
                self._reef_filter.addItem(key)
                # Disable trip name header row
                self._reef_filter.model().item(len(self._reef_filter) - 1).setEnabled(False)
                # set custom font to header to have it look differently
                self._reef_filter.model().item(len(self._reef_filter) - 1).setFont(self.headerRowfont)
                for each_reef in _reef_grouping[key] :
                   self._reef_filter.addItem(each_reef['name'], each_reef['id'])

            self._reef_filter.blockSignals(False)