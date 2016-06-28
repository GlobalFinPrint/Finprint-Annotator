from global_finprint import GlobalFinPrintServer, Observation
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from enum import IntEnum


class ContextMenu(QMenu):
    event_dialog = None

    class DialogActions(IntEnum):
        new_obs = 1
        add_event = 2
        edit_obs = 3
        edit_event = 4

    def __init__(self, current_set, parent):
        super(ContextMenu, self).__init__(parent)

        self.setStyleSheet('QMenu::item:selected { background-color: lightblue; }')

        # set
        self._set = current_set

        # animals
        self._grouping = {}
        for animal in self._set.animals:
            if animal.group not in self._grouping:
                self._grouping[animal.group] = []
            self._grouping[animal.group].append(animal)

        # actions
        self._animal_group_menu = self.addMenu('Organism')
        for group in self._grouping.keys():
            group_menu = self._animal_group_menu.addMenu(group)
            for animal in self._grouping[group]:
                act = group_menu.addAction(str(animal))
                act.setData(animal)
        self._interest_act = self.addAction('Of interest')
        self._observations_menu = self.addMenu('Add to existing observation')
        self._cancel_act = self.addAction('Cancel')

        # attributes
        def recur_attr(attrs):
            attr_list = []
            for attr in attrs:
                attr_list.append({'id': attr['id'], 'name': attr['name'], 'level': attr['level']})
                if 'children' in attr:
                    attr_list += recur_attr(attr['children'])
            return attr_list
        self._attributes = recur_attr(self._set.attributes)

        # event params
        self.dialog_values = {}

        # dialog controls
        self.att_dropdown = None
        self.animal_dropdown = None
        self.text_area = None
        self.obs_text = None
        self.selected_obs = None

    def _populate_obs_menu(self):
        self._observations_menu.clear()
        for obs in self._set.observations:
            act = self._observations_menu.addAction(str(obs))
            act.setData(obs)

    def display(self):
        self._populate_obs_menu()
        action = self.exec_(QCursor.pos())  # TODO position better
        if action is None or action == self._cancel_act:
            self.parent().clear_extent()
        elif action == self._interest_act:
            self.display_event_dialog(action=self.DialogActions.new_obs,
                                      type_choice='I')
        elif type(action.data()).__name__ == 'Animal':
            self.display_event_dialog(action=self.DialogActions.new_obs,
                                      type_choice='A',
                                      animal=action.data())
        elif type(action.data()).__name__ == 'Observation':
            self.display_event_dialog(action=self.DialogActions.add_event,
                                      obs=action.data())

    def display_event_dialog(self, **kwargs):
        self.event_dialog = QDialog(self, Qt.WindowTitleHint)
        self.event_dialog.setFixedWidth(300)
        self.event_dialog.setModal(True)
        self.event_dialog.setStyleSheet('background:#fff;')
        self.event_dialog.setWindowTitle('Event data')

        # set dialog data for submit
        if 'obs' in kwargs:
            self.selected_obs = kwargs['obs']
            kwargs['type_choice'] = kwargs['obs'].type_choice
            if kwargs['type_choice'] == 'A':
                kwargs['animal'] = kwargs['obs'].animal
                self.dialog_values['animal_id'] = kwargs['animal'].id
        else:
            self.dialog_values['type_choice'] = kwargs['type_choice']
            if self.dialog_values['type_choice'] == 'A' and 'animal' in kwargs:
                self.dialog_values['animal_id'] = kwargs['animal'].id
        self.dialog_values['event_time'] = int(self.parent().get_position())
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
        # TODO only editable on new obs/obs edit
        if 'animal' in kwargs:
            animal_label = QLabel('Animal:')
            self.animal_dropdown = QComboBox()
            animal_label.setBuddy(self.animal_dropdown)
            for an in self._set.animals:
                self.animal_dropdown.addItem(str(an), an.id)
            self.animal_dropdown.setCurrentIndex(self.animal_dropdown.findData(self.dialog_values['animal_id']))
            self.animal_dropdown.currentIndexChanged.connect(self.animal_select)
            layout.addWidget(animal_label)
            layout.addWidget(self.animal_dropdown)

        # attributes
        attributes_label = QLabel('Attribute:')
        self.att_dropdown = QComboBox()
        attributes_label.setBuddy(self.att_dropdown)
        self.att_dropdown.addItem('---')  # TODO require a value for submit
        for att in self._attributes:  # TODO multiple selection
            label = (att['level'] * '-') + (' ' if att['level'] > 0 else '') + att['name']
            self.att_dropdown.addItem(label, att['id'])
        self.att_dropdown.currentIndexChanged.connect(self.attribute_select)
        layout.addWidget(attributes_label)
        layout.addWidget(self.att_dropdown)

        # observation notes
        if kwargs['action'] in (self.DialogActions.new_obs, self.DialogActions.edit_obs):
            obs_notes_label = QLabel('Observation notes:')
            self.obs_text = QPlainTextEdit()
            if 'obs' in kwargs:
                self.obs_text.setPlainText(kwargs['obs'].comment)
            obs_notes_label.setBuddy(self.obs_text)
            self.obs_text.setFixedHeight(50)
            self.obs_text.textChanged.connect(self.obs_note_change)
            layout.addWidget(obs_notes_label)
            layout.addWidget(self.obs_text)

        # event notes
        notes_label = QLabel('Event notes:')
        self.text_area = QPlainTextEdit()
        notes_label.setBuddy(self.text_area)
        self.text_area.setFixedHeight(50)
        self.text_area.textChanged.connect(self.note_change)
        layout.addWidget(notes_label)
        layout.addWidget(self.text_area)

        # save/cancel buttons
        buttons = QDialogButtonBox()  # TODO style the buttons
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
        if 'type_choice' in self.dialog_values:  # new obs
            filename = self._set.add_observation(self.dialog_values)
        else:  # add event to obs
            filename = self._set.add_event(self.selected_obs.id, self.dialog_values)

        # update observation_table
        self.parent().parent()._observation_table.refresh_model()

        # save frame
        self.parent().save_image(filename)

        # close and clean up
        self.dialog_values = {}
        self.event_dialog.close()
        self.event_dialog = None
        self.parent().clear_extent()

    def pushed_cancel(self):
        self.dialog_values = {}
        self.event_dialog.close()
        self.event_dialog = None
        self.parent().clear_extent()

    def attribute_select(self):
        self.dialog_values['attribute'] = self.att_dropdown.itemData(self.att_dropdown.currentIndex())

    def animal_select(self):
        self.dialog_values['animal_id'] = self.animal_dropdown.itemData(self.animal_dropdown.currentIndex())

    def note_change(self):
        self.dialog_values['note'] = self.text_area.toPlainText()

    def obs_note_change(self):
        self.dialog_values['comment'] = self.obs_text.toPlainText()
