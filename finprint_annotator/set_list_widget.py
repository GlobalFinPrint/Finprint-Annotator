from pydispatch import dispatcher
from global_finprint import GlobalFinPrintServer
from PyQt4.QtGui import *
from PyQt4.QtCore import *


class SetListWidget(QWidget):

    def __init__(self):
        super(SetListWidget, self).__init__()

        self.set_list = QListWidget()
        self.set_list.setMinimumSize(600, 400)
        self.set_list.setFont(self._get_font())
        self.set_list.setSelectionMode(QAbstractItemView.SingleSelection)

        self.set_list.doubleClicked.connect(self.on_list_item_clicked)
        self.list_container = QVBoxLayout()
        self.list_container.addWidget(self.set_list)

        self.setLayout(self.list_container)

    def add_item(self, set):
        i = QListWidgetItem()
        if GlobalFinPrintServer().is_lead():
            i.setText('{0} - {1}'.format(set['set_code'], set['assigned_to']['user']))
        else:
            i.setText(set['set_code'])
        i.setData(Qt.UserRole, set)
        self.set_list.addItem(i)

    def _get_font(self):
        font = QFont()
        font.setPointSize(14)
        return font

    def on_list_item_clicked(self, index):
        dispatcher.send('SET_SELECTED', dispatcher.Anonymous, value=self.set_list.currentItem().data(Qt.UserRole))
