from .components import ClickLabel
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class AutocompleteMenu(QWidgetAction):
    FONT_SIZE = 14

    def __init__(self, title, choices, parent):
        super().__init__(parent)
        self.title = title
        self.choices = choices

        default_widget = QWidget()
        default_widget.setFixedWidth(300)  # TODO update with toggle_view
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        top_section = QWidget()
        top_section.setStyleSheet('border-bottom: 1px solid #ccc;')
        top_layout = QHBoxLayout()

        self.line_edit = QLineEdit()
        font = self.line_edit.font()
        font.setPointSize(self.FONT_SIZE)
        self.line_edit.setFont(font)
        self.line_edit.textChanged.connect(self._text_changed)

        self.toggle_view = ClickLabel()
        self.toggle_view.setPixmap(QPixmap('images/fullscreen.png'))

        top_layout.addWidget(self.line_edit)
        top_layout.addWidget(self.toggle_view)
        top_section.setLayout(top_layout)

        self.choice_list = QListWidget()
        for choice in choices:
            choice_item = QListWidgetItem(str(choice))
            choice_item.setData(Qt.UserRole, choice.id)
            self.choice_list.addItem(choice_item)
        self.choice_list.setStyleSheet('''
        :focus { border: none; }
        QScrollBar::vertical { border: 1px solid #999999; background:white; width:10px; margin: 0px 0px 0px 0px;}
        QScrollBar::handle:vertical { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop: 0  rgb(131,140,158),
            stop: 0.5 rgb(131,140,158),  stop:1 rgb(131,140,158)); min-height: 0px;}
        QScrollBar::add-line:vertical { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop: 0 rgb(131,140,158),
            stop: 0.5 rgb(131,140,158),  stop:1 rgb(131,140,158)); height: 0px; subcontrol-position: bottom;
            subcontrol-origin: margin;}
        QScrollBar::sub-line:vertical { background: qlineargradient(x1:0, y1:0, x2:1, y2:0," stop: 0 rgb(131,140,158),
            stop: 0.5 rgb(131,140,158),  stop:1 rgb(131,140,158)); height: 0px;subcontrol-position: top;
            subcontrol-origin:margin}
        QScrollBar::horizontal { border: 1px solid #999999; background:white; height:10px; margin: 0px 0px 0px 0px;}
        QScrollBar::handle:horizontal { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop: 0 rgb(131,140,158),
            stop: 0.5 rgb(131,140,158),  stop:1 rgb(131,140,158)); min-width: 0px;}
        QScrollBar::add-line:horizontal { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop: 0 rgb(131,140,158),
            stop: 0.5 rgb(131,140,158),  stop:1 rgb(131,140,158)); width: 0px; subcontrol-position: right;
            subcontrol-origin: margin;}
        QScrollBar::sub-line:horizontal { background: qlineargradient(x1:0, y1:0, x2:1, y2:0," stop: 0 rgb(131,140,158),
            stop: 0.5 rgb(131,140,158),  stop:1 rgb(131,140,158)); width: 0px;subcontrol-position: left;
            subcontrol-origin:margin}
        ''')
        font = self.choice_list.font()
        font.setPointSize(self.FONT_SIZE)
        self.choice_list.setFont(font)

        layout.addWidget(top_section)
        layout.addWidget(self.choice_list)
        default_widget.setLayout(layout)
        self.setDefaultWidget(default_widget)

    def _text_changed(self, new_text):
        if new_text == '':
            for row in range(0, self.choice_list.count()):
                self.choice_list.item(row).setHidden(False)
        else:
            for row in range(0, self.choice_list.count()):
                item = self.choice_list.item(row)
                item.setHidden(new_text not in item.text())
