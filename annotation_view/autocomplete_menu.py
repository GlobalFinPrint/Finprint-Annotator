from .components import ClickLabel
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class AutocompleteMenu(QWidgetAction):
    def __init__(self, title, choices, parent):
        super().__init__(parent)
        self.title = title
        self.choices = choices

        default_widget = QWidget()
        layout = QVBoxLayout()

        top_section = QWidget()
        top_layout = QHBoxLayout()
        self.line_edit = QLineEdit()
        self.toggle_view = ClickLabel()
        self.toggle_view.setPixmap(QPixmap('images/fullscreen.png'))
        top_layout.addWidget(self.line_edit)
        top_layout.addWidget(self.toggle_view)
        top_section.setLayout(top_layout)

        self.choice_list = QListWidget()
        for choice in choices:
            self.choice_list.addItem(str(choice))

        layout.addWidget(top_section)
        layout.addWidget(self.choice_list)
        default_widget.setLayout(layout)
        self.setDefaultWidget(default_widget)
