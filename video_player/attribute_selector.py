from PyQt4.QtCore import *
from PyQt4.QtGui import *
from global_finprint import GlobalFinPrintServer


BUTTONS_PER_ROW = 2
MARK_ZERO_TIME_ID = 16
DEFAULT_ATTRIBUTE_TAG = '--- select one or more tags ---'

class SelectedButton(QPushButton):
    clicked = pyqtSignal(int)

    def __init__(self, text, attr_id):
        super().__init__(text)
        self.setStyleSheet('padding: 5px;')
        self.setProperty('id', attr_id)
        self.pressed.connect(self.pressed_event)

    def pressed_event(self):
        self.clicked.emit(self.property('id'))


class AttributeSelector(QVBoxLayout):
    selected_changed = pyqtSignal()

    def __init__(self, attributes, selected_ids, observation_list = None):
        super().__init__()
        self.label = QLabel('Tags:')
        self.input_line = QLineEdit()
        self.attributes = self._make_attr_list(attributes, [] if selected_ids is None else selected_ids)
        self.model = QStandardItemModel(self)
        self.completer = CustomQCompleter(self,model=self.model)
        self.selected_items = QButtonGroup(self)
        self.selected_layout = QGridLayout()
        self.observation_list = observation_list

        self._refresh_list()

        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setModel(self.model)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setCompletionColumn(0)
        self.completer.activated.connect(self.on_select, Qt.QueuedConnection)

        self.label.setBuddy(self.input_line)
        self.input_line.setCompleter(self.completer)

        self.addWidget(self.label)
        self.addWidget(self.input_line)
        self.addLayout(self.selected_layout)

        self.display_selected()

    def get_selected_ids(self):
        return [attr['id'] for attr in self.attributes if attr['selected']]

    def on_select(self, text, showCurrent = False):
            flag = 0
            for attr in self.attributes:
                if attr['name'] == text:
                    flag = 1
                    attr['selected'] = True
                    break
            # Added for DEFAULT_ATTRIBUTE_TAG
            if DEFAULT_ATTRIBUTE_TAG == text or flag == 0:
                default_att_list = [att for att in self.attributes if att['name']==DEFAULT_ATTRIBUTE_TAG]
                if len(default_att_list) == 0 :
                    self.attributes.append({
                        'id': -1 ,
                        'name': DEFAULT_ATTRIBUTE_TAG,
                        'level': -1,
                        'selected': True
                    })
                else :
                    default_att_list[0]['selected'] = True

            self.selected_changed.emit()
            self.empty_selected()
            self.display_selected()
            if flag == 1 and showCurrent :
             self.input_line.setText(text)
            else :
                self.input_line.setText(text)




    def empty_selected(self):
        for i in reversed(range(self.selected_layout.count())):
            self.selected_layout.itemAt(i).widget().deleteLater()

        for button in self.selected_items.buttons():
            self.selected_items.removeButton(button)

    def display_selected(self):
        spot = 0
        for attr in self.attributes:
            if attr['selected']:
                button = SelectedButton(attr['name'] + '  (X)', attr['id'])
                button.clicked.connect(self._unselect_tag)
                if attr['id'] != -1 :
                 self.selected_items.addButton(button)
                 self.selected_layout.addWidget(button, *divmod(spot, BUTTONS_PER_ROW))
                 spot += 1

    def _unselect_tag(self, id):
      if self.observation_list is None or  id !=MARK_ZERO_TIME_ID or self.observation_list is not None and len(self.observation_list) > 0 or GlobalFinPrintServer().is_lead():
        for attr in self.attributes:
            if attr['id'] == id:
                attr['selected'] = False
        self.selected_changed.emit()
        self.empty_selected()
        self.display_selected()
        self.input_line.setText('')
        #added for default tag
        default_att_list = [att for att in self.attributes if att['name'] == DEFAULT_ATTRIBUTE_TAG]
        if len(default_att_list) == 0:
            self.attributes.append({
                'id': -1,
                'name': DEFAULT_ATTRIBUTE_TAG,
                'level': -1,
                'selected': True
            })
        else :
            default_att_list[0]['selected'] = True
      self.selected_changed.emit()
      self.empty_selected()
      self.display_selected()
      self.input_line.setText(DEFAULT_ATTRIBUTE_TAG)


    def _refresh_list(self):
        for attr in self.attributes:
            self._add_item(attr['name'], attr['id'], attr['selected'])

    def _add_item(self, *items):
        self.model.appendRow([QStandardItem(item) for item in items])

    def _make_attr_list(self, attributes, selected_ids):
        attr_list = []
        for attr in attributes:
            if not attr['not_selectable']:
                attr_list.append({
                    'id': attr['id'],
                    'name': attr['verbose'],
                    'level': attr['level'],
                    'selected': attr['id'] in selected_ids
                })
            if 'children' in attr:
                attr_list += self._make_attr_list(attr['children'], selected_ids)

        return attr_list

    def return_mark_zero_attr(self):
        for attr in self.attributes  :
           if attr['id'] == MARK_ZERO_TIME_ID:
               return attr


class CustomQCompleter(QCompleter):
    def __init__(self, parent=None, model=None):
        super(CustomQCompleter, self).__init__(parent)
        self.local_completion_prefix = ""
        self.source_model = model

    def updateModel(self):
        if 'select one or more tags' in self.local_completion_prefix or '---' in self.local_completion_prefix :
            self.parent().input_line.clear()
            if len(self.local_completion_prefix) > len(DEFAULT_ATTRIBUTE_TAG) :
              self.parent().input_line.setText(self.local_completion_prefix[len(DEFAULT_ATTRIBUTE_TAG):])
              self.local_completion_prefix = self.local_completion_prefix[len(DEFAULT_ATTRIBUTE_TAG):]
            else :
              self.local_completion_prefix = ''

        local_completion_prefix = self.local_completion_prefix
        class InnerProxyModel(QSortFilterProxyModel):
            def filterAcceptsRow(self, sourceRow, sourceParent):
                index0 = self.sourceModel().index(sourceRow, 0, sourceParent)
                return local_completion_prefix.lower() in self.sourceModel().data(index0).lower()
        proxy_model = InnerProxyModel()
        proxy_model.setSourceModel(self.source_model)
        super(CustomQCompleter, self).setModel(proxy_model)

    def splitPath(self, path):
        self.local_completion_prefix = path
        self.updateModel()
        return ""