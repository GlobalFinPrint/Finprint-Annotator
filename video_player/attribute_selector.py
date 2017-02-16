from PyQt4.QtCore import *
from PyQt4.QtGui import *


BUTTONS_PER_ROW = 2


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

    def __init__(self, attributes, selected_ids):
        super().__init__()
        self.label = QLabel('Tags:')
        self.input_line = QLineEdit()
        self.attributes = self._make_attr_list(attributes, [] if selected_ids is None else selected_ids)
        self.model = QStandardItemModel(self)
        self.completer = QCompleter(self)
        self.selected_items = QButtonGroup(self)
        self.selected_layout = QGridLayout()

        self._refresh_list()

        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
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

    def on_select(self, text):
        for attr in self.attributes:
            if attr['name'] == text:
                attr['selected'] = True
                break
        self.selected_changed.emit()
        self.empty_selected()
        self.display_selected()
        self.input_line.setText('')

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
                self.selected_items.addButton(button)
                self.selected_layout.addWidget(button, *divmod(spot, BUTTONS_PER_ROW))
                spot += 1

    def _unselect_tag(self, id):
        for attr in self.attributes:
            if attr['id'] == id:
                attr['selected'] = False
        self.selected_changed.emit()
        self.empty_selected()
        self.display_selected()

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
