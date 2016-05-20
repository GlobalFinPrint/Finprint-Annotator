from PyQt4.QtCore import *


class Highlighter(object):
    def __init__(self):
        self._highlight_corner1 = QPoint(0, 0)
        self._highlight_corner2 = QPoint(0, 0)

    def get_rect(self):
        return QRect(self._highlight_corner1.x(),
                     self._highlight_corner1.y(),
                     self._highlight_corner2.x() - self._highlight_corner1.x(),
                     self._highlight_corner2.y() - self._highlight_corner1.y())

    def start_rect(self, pos):
        self._highlight_corner1 = pos
        self._highlight_corner2 = pos

    def set_rect(self, pos):
        self._highlight_corner2 = pos

    def clear(self):
        self.start_rect(QPoint(0, 0))
