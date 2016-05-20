from global_finprint import Animal
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class MenuButton(QPushButton):
    item_select = pyqtSignal(Animal)

    def __init__(self, *args, **kw):
        QPushButton.__init__(self, *args, **kw)
        self.last_mouse_pos = None

    def mousePressEvent(self, event):
        self.last_mouse_pos = event.pos()
        QPushButton.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        self.last_mouse_pos = event.pos()
        QPushButton.mouseReleaseEvent(self, event)

    def get_last_pos(self):
        if self.last_mouse_pos:
            return self.mapToGlobal(self.last_mouse_pos)
        else:
            return None
