from PyQt4.QtCore import *
from PyQt4.QtGui import *


class ContextMenu(QMenu):
    def __init__(self, set):
        super(ContextMenu, self).__init__()

        # set
        self._set = set

        # actions
        self._animal_act = self.addAction('Organism >')
        self._interest_act = self.addAction('Of interest')
        self._existing_act = self.addAction('Add to existing observation >')
        self._cancel_act = self.addAction('Cancel')

        # animals
        self._grouping = {}
        for animal in set.animals:
            if animal.group not in self._grouping:
                self._grouping[animal.group] = []
            self._grouping[animal.group].append(animal)

        # attributes
        # TODO

    def display(self, pos):
        action = self.exec_(QCursor.pos())  # TODO position better
        if action == self._animal_act:
            self.display_animals()
        elif action == self._interest_act:
            self.display_event_dialog(obs_type='I')
            pass
        elif action == self._existing_act:
            # TODO list observations
            # TODO need str representation
            # TODO open add/edit dialog
            pass
        elif action == self._cancel_act:
            pass  # close menu

    def display_animals(self):
        groups = QMenu()
        for group in self._grouping.keys():
            groups.addAction(group + ' >')
        group_action = groups.exec_(QCursor.pos())
        selected_group = group_action.text()[:-2]
        if selected_group in self._grouping.keys():
            animals = QMenu()
            for animal in self._grouping[selected_group]:
                animals.addAction(str(animal))
            selected_animal = animals.exec_(QCursor.pos())
            if selected_animal != 0:
                self.display_event_dialog(obs_type='A', animal=selected_animal.text())

    def display_event_dialog(self, obs=None, obs_type=None, **kwargs):
        dialog = QDialog(self, Qt.WindowTitleHint)
        dialog.setFixedWidth(300)
        dialog.setModal(True)
        dialog.setStyleSheet('background:#fff;')
        dialog.setWindowTitle('Event data')

        layout = QVBoxLayout()

        obs_label = QLabel('Observation: ' + ('New' if obs is None else str(obs)))
        layout.addWidget(obs_label)

        type_label = QLabel('Observation type: ' + ('Of interest' if obs_type == 'I' else 'Animal'))
        layout.addWidget(type_label)

        if 'animal' in kwargs:
            animal_label = QLabel('Animal: ' + kwargs['animal'])
            layout.addWidget(animal_label)

        notes_label = QLabel('Notes:')
        text_area = QPlainTextEdit()
        notes_label.setBuddy(text_area)
        text_area.setFixedHeight(50)
        layout.addWidget(notes_label)
        layout.addWidget(text_area)

        buttons = QDialogButtonBox()
        save_but = QPushButton('Save')
        save_but.setFixedHeight(30)
        cancel_but = QPushButton('Cancel')
        cancel_but.setFixedHeight(30)
        buttons.addButton(save_but, QDialogButtonBox.ActionRole)
        buttons.addButton(cancel_but, QDialogButtonBox.ActionRole)
        layout.addWidget(buttons)

        dialog.setLayout(layout)
        dialog.show()
