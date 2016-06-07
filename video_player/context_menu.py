from PyQt4.QtCore import *
from PyQt4.QtGui import *


class ContextMenu(QMenu):
    event_dialog = None

    def __init__(self, current_set, parent):
        super(ContextMenu, self).__init__(parent)

        # set
        self._set = current_set

        # actions
        self._animal_act = self.addAction('Organism >')
        self._interest_act = self.addAction('Of interest')
        self._existing_act = self.addAction('Add to existing observation >')
        self._cancel_act = self.addAction('Cancel')

        # animals
        self._grouping = {}
        for animal in self._set.animals:
            if animal.group not in self._grouping:
                self._grouping[animal.group] = []
            self._grouping[animal.group].append(animal)

        # attributes
        self._attributes = {}
        for att_dict in self._set.attributes:
            self._attributes[att_dict['id']] = att_dict['name']

        # event params
        self.dialog_values = {}

        # dialog controls
        self.att_dropdown = None
        self.text_area = None

    def display(self):
        action = self.exec_(QCursor.pos())  # TODO position better
        if action == self._animal_act:
            self.display_animals()
        elif action == self._interest_act:
            self.display_event_dialog(type_choice='I')
        elif action == self._existing_act:
            self.display_observations()
        elif action == self._cancel_act:
            pass

    def display_observations(self):
        observations = QMenu()
        for obs in self._set.observations:
            act = observations.addAction(str(obs))
            act.setData(obs)
        selected_obs = observations.exec_(QCursor.pos())
        self.display_event_dialog(obs=selected_obs.data())

    def display_animals(self):
        groups = QMenu()
        for group in self._grouping.keys():
            groups.addAction(group + ' >')
        group_action = groups.exec_(QCursor.pos())
        selected_group = group_action.text()[:-2]
        if selected_group in self._grouping.keys():
            animals = QMenu()
            for animal in self._grouping[selected_group]:
                act = animals.addAction(str(animal))
                act.setData(animal)
            selected_animal = animals.exec_(QCursor.pos())
            if selected_animal != 0:
                self.display_event_dialog(type_choice='A', animal=selected_animal.data())

    def display_event_dialog(self, **kwargs):
        self.event_dialog = QDialog(self, Qt.WindowTitleHint)
        self.event_dialog.setFixedWidth(300)
        self.event_dialog.setModal(True)
        self.event_dialog.setStyleSheet('background:#fff;')
        self.event_dialog.setWindowTitle('Event data')

        # set dialog data for submit
        if 'obs' in kwargs:
            kwargs['type_choice'] = kwargs['obs'].type_choice
            if kwargs['type_choice'] == 'A':
                kwargs['animal'] = kwargs['obs'].animal
        else:
            self.dialog_values['type_choice'] = kwargs['type_choice']
            if self.dialog_values['type_choice'] == 'A' and 'animal' in kwargs:
                self.dialog_values['animal_id'] = kwargs['animal'].id
        self.dialog_values['event_time'] = self.parent().get_position()
        self.dialog_values['extent'] = self.parent().get_highlight_extent().to_wkt()
        self.dialog_values['note'] = ''
        self.dialog_values['attribute'] = None

        # set up dialog view
        layout = QVBoxLayout()

        # observation
        obs_label = QLabel('Observation: ' + (str(kwargs['obs']) if 'obs' in kwargs else 'New'))
        layout.addWidget(obs_label)

        # obs type
        type_label = QLabel('Observation type: ' + ('Of interest' if kwargs['type_choice'] == 'I' else 'Animal'))
        layout.addWidget(type_label)

        # obs animal (if applicable)
        if 'animal' in kwargs:
            animal_label = QLabel('Animal: ' + str(kwargs['animal']))
            layout.addWidget(animal_label)

        # attributes
        attributes_label = QLabel('Attribute:')
        self.att_dropdown = QComboBox()
        attributes_label.setBuddy(self.att_dropdown)
        self.att_dropdown.addItem('---')
        for id, att in self._attributes.items():
            self.att_dropdown.addItem(att, id)
        self.att_dropdown.currentIndexChanged.connect(self.attribute_select)
        layout.addWidget(attributes_label)
        layout.addWidget(self.att_dropdown)

        # notes
        notes_label = QLabel('Notes:')
        self.text_area = QPlainTextEdit()
        notes_label.setBuddy(self.text_area)
        self.text_area.setFixedHeight(50)
        self.text_area.textChanged.connect(self.note_change)
        layout.addWidget(notes_label)
        layout.addWidget(self.text_area)

        # save/cancel buttons
        buttons = QDialogButtonBox()
        save_but = QPushButton('Save')
        save_but.setFixedHeight(30)
        save_but.clicked.connect(self.pushed_save)
        cancel_but = QPushButton('Cancel')
        cancel_but.setFixedHeight(30)
        cancel_but.clicked.connect(self.pushed_cancel)
        buttons.addButton(save_but, QDialogButtonBox.ActionRole)
        buttons.addButton(cancel_but, QDialogButtonBox.ActionRole)
        layout.addWidget(buttons)

        self.event_dialog.setLayout(layout)
        self.event_dialog.show()

    def pushed_save(self):
        from logging import getLogger; getLogger('finprint').info(self.dialog_values)
        if 'type_choice' in self.dialog_values:  # new obs
            pass
        else:  # add event to obs
            pass
        self.dialog_values = {}
        self.event_dialog.close()
        self.event_dialog = None
        self.parent().play()

    def pushed_cancel(self):
        self.dialog_values = {}
        self.event_dialog.close()
        self.event_dialog = None
        self.parent().play()

    def attribute_select(self):
        self.dialog_values['attribute'] = self.att_dropdown.itemData(self.att_dropdown.currentIndex())

    def note_change(self):
        self.dialog_values['note'] = self.text_area.toPlainText()
