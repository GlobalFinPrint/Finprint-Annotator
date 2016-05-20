import re
from PyQt4.QtCore import *


class Extent(object):
    def __init__(self):
        self.empty = True
        self.rect = QRect(QPoint(0, 0), QPoint(0, 0))
        self.height = 1
        self.width = 1
        self.numbers = []

    def getRect(self, h, w):
        self.height = h
        self.width = w
        if len(self.numbers) == 10:
            self.rect = QRect(QPoint(self._adjustX(float(self.numbers[0])), self._adjustY(float(self.numbers[1]))),
                              QPoint(self._adjustX(float(self.numbers[4])), self._adjustY(float(self.numbers[5]))))
        return self.rect

    def setRect(self, r, h, w):
        self.empty = False
        self.rect = r
        self.height = h
        self.width = w

    def from_wkt(self, wkt_polygon):
        self.empty = False
        # Comes in SRID=4356;POLYGON ((X1 Y1, X2 Y1, X2 Y2, X1 Y2, X1 Y1))
        self.numbers = re.findall(r'\d+(?:\.\d*)?', wkt_polygon.partition(';')[2])

    def _adjustX(self, x):
        return x * self.width

    def _adjustY(self, y):
        return y * self.height

    def _normalizeX(self, x):
        return x/self.width

    def _normalizeY(self, y):
        return y/self.height

    def to_wkt(self):
        wkt = "POLYGON (({0:.5f} {1:.5f}, {2:.5f} {3:.5f}, {4:.5f} {5:.5f}, {6:.5f} {7:.5f}, {8:.5f} {9:.5f}))"
        return wkt.format(self._normalizeX(self.rect.topLeft().x()),
                          self._normalizeY(self.rect.topLeft().y()),
                          self._normalizeX(self.rect.topRight().x()), self._normalizeY(self.rect.topRight().y()),
                          self._normalizeX(self.rect.bottomRight().x()), self._normalizeY(self.rect.bottomRight().y()),
                          self._normalizeX(self.rect.bottomLeft().x()), self._normalizeY(self.rect.bottomLeft().y()),
                          self._normalizeX(self.rect.topLeft().x()), self._normalizeY(self.rect.topLeft().y()))
