from PyQt4.QtCore import *
from PyQt4.QtGui import *
import re


class AttributeSelector(QComboBox):
    selected_changed = pyqtSignal()

    def __init__(self, attrs, selected_ids=None):
        super().__init__()
        self.view().pressed.connect(self.item_pressed)
        self.setModel(QStandardItemModel(self))
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.setStyleSheet('QComboBox QAbstractItemView { margin-top: 27px; }')

        self.currentIndexChanged.connect(self.on_current_index_change)

        self.done_button = QPushButton(parent=self.view())
        self.done_button.setText('Done')
        self.done_button.setVisible(False)
        self.done_button.setFixedSize(200, 25)
        self.done_button.pressed.connect(self.done_pressed)

        attrs = self._make_attr_list(attrs)
        if selected_ids is None:
            selected_ids = []

        for attr in attrs:
            label = (attr['level'] * '--') + (' ' if attr['level'] > 0 else '') + attr['name']
            self.addItem(label, attr['id'])
            index = self.findData(attr['id'])
            item = self.model().item(index, 0)
            item.setCheckState(Qt.Checked if attr['id'] in selected_ids else Qt.Unchecked)

        self.update_button_text()

    def get_selected(self):
        return [self.itemData(i) for i in range(self.count()) if self.model().item(i).checkState() == Qt.Checked]

    def get_selected_text(self):
        clean_text = re.compile(r'(^-+\s)?(.*)$')
        selected_text = [clean_text.match(self.itemText(i)).groups()[-1] for i in range(self.count())
                         if self.model().item(i).checkState() == Qt.Checked]
        return ', '.join(selected_text) if len(selected_text) > 0 else '--- NONE ---'

    def update_button_text(self):
        self.lineEdit().setText(self.get_selected_text())

    def item_pressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)
        self.selected_changed.emit()

    def done_pressed(self):
        self.done_button.setVisible(False)
        super().hidePopup()

    def showPopup(self):
        super().showPopup()
        self.done_button.setVisible(True)

    def hidePopup(self):
        pass  # stay open (press escape to close)

    def on_current_index_change(self, *args, **kwargs):
        self.update_button_text()

    def _all_items(self):
        return [self.itemText(i) for i in range(self.count())]

    def _make_attr_list(self, attrs):
        attr_list = []
        for attr in attrs:
            attr_list.append({'id': attr['id'], 'name': attr['name'], 'level': attr['level']})
            if 'children' in attr:
                attr_list += self._make_attr_list(attr['children'])
        return attr_list
