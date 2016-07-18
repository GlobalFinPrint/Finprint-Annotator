from PyQt4.QtCore import *
from PyQt4.QtGui import *


class SelectedButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        # TODO style button


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
        self.selected_layout = QVBoxLayout()

        self._refresh_list()

        self.completer.setModel(self.model)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setCompletionColumn(0)
        self.completer.activated.connect(self.on_select)

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
        self.display_selected()

    def empty_selected(self):
        for button in self.selected_items.buttons():
            self.selected_items.removeButton(button)
            self.selected_layout.removeWidget(button)

    def display_selected(self):
        self.empty_selected()
        for attr in self.attributes:
            if attr['selected']:
                button = SelectedButton(attr['name'])
                button.setProperty('id', attr['id'])
                self.selected_items.addButton(button)
                self.selected_layout.addWidget(button)

    def _refresh_list(self):
        for attr in self.attributes:
            self._add_item(attr['name'], attr['id'], attr['selected'])

    def _add_item(self, *items):
        self.model.appendRow([QStandardItem(item) for item in items])

    def _make_attr_list(self, attributes, selected_ids):
        attr_list = []
        for attr in attributes:
            attr_list.append({
                'id': attr['id'],
                'name': attr['name'],
                'level': attr['level'],
                'selected': attr['id'] in selected_ids
            })
            if 'children' in attr:
                attr_list += self._make_attr_list(attr['children'], selected_ids)
        return attr_list
