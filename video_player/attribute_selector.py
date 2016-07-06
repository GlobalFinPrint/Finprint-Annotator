from PyQt4.QtCore import *
from PyQt4.QtGui import *


class AttributeSelector(QLineEdit):
    selected_changed = pyqtSignal()

    def __init__(self, attributes, selected_ids):
        super().__init__()
        self.attributes = self._make_attr_list(attributes, [] if selected_ids is None else selected_ids)
        self.model = QStandardItemModel(self)
        self.completer = QCompleter(self)

        self._refresh_list()

        self.completer.setModel(self.model)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setCompletionColumn(0)

        self.setCompleter(self.completer)

    def get_selected(self):
        return [att['id'] for att in self.attributes if att['selected']]

    def _refresh_list(self):
        for att in self.attributes:
            self._add_item(('---' * att['level']) + att['name'], att['id'], att['selected'])

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
