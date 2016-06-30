from PyQt4.QtCore import *
from PyQt4.QtGui import *


class AttributeSelector(QComboBox):
    selected_changed = pyqtSignal()

    def __init__(self, attrs, selected_ids=None):
        super().__init__()
        self.view().pressed.connect(self.item_pressed)
        self.setModel(QStandardItemModel(self))

        attrs = self._make_attr_list(attrs)
        if selected_ids is None:
            selected_ids = []

        for attr in attrs:
            label = (attr['level'] * '--') + (' ' if attr['level'] > 0 else '') + attr['name']
            self.addItem(label, attr['id'])
            index = self.findData(attr['id'])
            item = self.model().item(index, 0)
            item.setCheckState(Qt.Checked if attr['id'] in selected_ids else Qt.Unchecked)

    def get_selected(self):
        return [self.itemData(i) for i in range(self.count()) if self.model().item(i).checkState() == Qt.Checked]

    def item_pressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)
        self.selected_changed.emit()

    def _all_items(self):
        return [self.itemText(i) for i in range(self.count())]

    def _make_attr_list(self, attrs):
        attr_list = []
        for attr in attrs:
            attr_list.append({'id': attr['id'], 'name': attr['name'], 'level': attr['level']})
            if 'children' in attr:
                attr_list += self._make_attr_list(attr['children'])
        return attr_list
