from global_finprint import Animal
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class OrganismSelector(QObject):
    item_select = pyqtSignal(Animal, int)

    def __init__(self, animal_menu):
        super(QObject, self).__init__()
        self.menus = []
        self.animal_menu = animal_menu

    def popup_menu(self, pos, row = -1):
        def _make_action(data, row):
            return lambda: self.item_select.emit(data, row)

        top_menu = QMenu('Organisms')
        for group in self.animal_menu:
            obsmenu = QMenu(group)
            for animal in self.animal_menu[group]:
                obsmenu.addAction(str(animal)).triggered.connect(_make_action(animal, row))
            self.menus.append(obsmenu)
            top_menu.addMenu(obsmenu)

        top_menu.exec_(pos)
