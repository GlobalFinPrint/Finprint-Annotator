from .attribute_selector import AttributeSelector
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from enum import IntEnum


class DialogActions(IntEnum):
    new_obs = 1
    add_event = 2
    edit_obs = 3
    edit_event = 4


class ContextMenu(QMenu):
    event_dialog = None
    action = None
    itemSelected = pyqtSignal(dict)

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

    def _populate_obs_menu(self):
        self._observations_menu.clear()
        self._set.observations.sort(key=lambda o: o.initial_time())
        for obs in self._set.observations:
            act = self._observations_menu.addAction(str(obs))
            act.setData(obs)

    def display(self):
        self._populate_obs_menu()
        action = self.exec_(QCursor.pos())  # TODO position better
        if action is None or action == self._cancel_act:
            return None
        elif action == self._interest_act:
            self.itemSelected.emit({"action": DialogActions.new_obs,
                                    "type_choice": 'I'})
        elif type(action.data()).__name__ == 'Animal':
            self.itemSelected.emit({"action": DialogActions.new_obs,
                                    "type_choice": 'A',
                                    "animal": action.data()})
        elif type(action.data()).__name__ == 'Observation':
            self.itemSelected.emit({"action": DialogActions.add_event,
                                    "obs": action.data()})


class EventDialog(QDialog):
    def __init__(self, parent=None, flags=Qt.WindowTitleHint):
        super(EventDialog, self).__init__(parent=parent, flags=flags)

        self.setFixedWidth(300)  # TODO bigger for tag selector?
        self.setModal(True)
        self.setStyleSheet('background:#fff;')
        self.finished.connect(self.cleanup)

        # event params
        self.dialog_values = {}

        # dialog controls
        self.att_dropdown = None
        self.animal_dropdown = None
        self.text_area = None
        self.obs_text = None
        self.selected_obs = None
        self.selected_event = None

    def launch(self, kwargs):
        self.action = kwargs['action']

        if kwargs['action'] == DialogActions.new_obs:
            title = 'New observation'
        elif kwargs['action'] == DialogActions.add_event:
            title = 'Add event'
        elif kwargs['action'] == DialogActions.edit_obs:
            title = 'Edit observation'
        elif kwargs['action'] == DialogActions.edit_event:
            title = 'Edit event'
        else:
            title = ''  # should never happen
        self.setWindowTitle(title)

        self.dialog_values['note'] = ''
        self.dialog_values['attribute'] = None
        self._set = kwargs['set']

        # set dialog data for submit
        if 'obs' in kwargs:
            self.selected_obs = kwargs['obs']
            kwargs['type_choice'] = kwargs['obs'].type_choice
            if kwargs['type_choice'] == 'A':
                kwargs['animal'] = kwargs['obs'].animal
                self.dialog_values['animal_id'] = kwargs['animal'].id
        elif 'event' in kwargs:
            self.selected_event = kwargs['event']
            self.dialog_values['note'] = self.selected_event.note
            self.dialog_values['attribute'] = [a['id'] for a in self.selected_event.attribute]
        else:
            self.dialog_values['type_choice'] = kwargs['type_choice']
            if self.dialog_values['type_choice'] == 'A' and 'animal' in kwargs:
                self.dialog_values['animal_id'] = kwargs['animal'].id

        if kwargs['action'] in [DialogActions.new_obs, DialogActions.add_event]:
            self.dialog_values['event_time'] = kwargs['event_time']
            self.dialog_values['extent'] = kwargs['extent']

        # set up dialog view
        layout = QVBoxLayout()

        # observation info
        if kwargs['action'] != DialogActions.edit_event:
            obs_label = QLabel('Observation: ' + (str(kwargs['obs']) if 'obs' in kwargs else 'New'))
            type_label = QLabel(
                'Observation type: ' + ('Of interest' if kwargs['type_choice'] == 'I' else 'Animal'))
            layout.addWidget(obs_label)
            layout.addWidget(type_label)

        # obs animal (if applicable)
        if kwargs['action'] in [DialogActions.new_obs, DialogActions.edit_obs] and kwargs['type_choice'] == 'A':
            animal_label = QLabel('Organism:')
            self.animal_dropdown = QComboBox()
            animal_label.setBuddy(self.animal_dropdown)
            for an in self._set.animals:
                self.animal_dropdown.addItem(str(an), an.id)
            self.animal_dropdown.setCurrentIndex(self.animal_dropdown.findData(self.dialog_values['animal_id']))
            self.animal_dropdown.currentIndexChanged.connect(self.animal_select)
            layout.addWidget(animal_label)
            layout.addWidget(self.animal_dropdown)

        # attributes
        if kwargs['action'] != DialogActions.edit_obs:
            self.att_dropdown = AttributeSelector(self._set.attributes, self.dialog_values['attribute'])
            self.att_dropdown.selected_changed.connect(self.attribute_select)
            layout.addLayout(self.att_dropdown)

        # observation notes
        if kwargs['action'] in [DialogActions.new_obs, DialogActions.edit_obs]:
            obs_notes_label = QLabel('Observation Note:')
            self.obs_text = QPlainTextEdit()
            if 'obs' in kwargs:
                self.obs_text.setPlainText(kwargs['obs'].comment)
            obs_notes_label.setBuddy(self.obs_text)
            self.obs_text.setFixedHeight(50)
            self.obs_text.textChanged.connect(self.obs_note_change)
            layout.addWidget(obs_notes_label)
            layout.addWidget(self.obs_text)

        # event notes
        if kwargs['action'] != DialogActions.edit_obs:
            notes_label = QLabel('Image notes:')
            self.text_area = QPlainTextEdit()
            self.text_area.setPlainText(self.dialog_values['note'])
            notes_label.setBuddy(self.text_area)
            self.text_area.setFixedHeight(50)
            self.text_area.textChanged.connect(self.note_change)
            layout.addWidget(notes_label)
            layout.addWidget(self.text_area)

        # save/update/cancel buttons
        buttons = QDialogButtonBox()  # TODO style the buttons
        save_but = QPushButton('Save')
        save_but.setFixedHeight(30)
        save_but.clicked.connect(self.pushed_save)

        update_but = QPushButton('Update')
        update_but.setFixedHeight(30)
        update_but.clicked.connect(self.pushed_update)

        cancel_but = QPushButton('Cancel')
        cancel_but.setFixedHeight(30)
        cancel_but.clicked.connect(self.cleanup)

        if kwargs['action'] in [DialogActions.new_obs, DialogActions.add_event]:
            buttons.addButton(save_but, QDialogButtonBox.ActionRole)
        else:
            buttons.addButton(update_but, QDialogButtonBox.ActionRole)
        buttons.addButton(cancel_but, QDialogButtonBox.ActionRole)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.show()

    def pushed_save(self):
        if self.action == DialogActions.new_obs:  # new obs
            filename = self._set.add_observation(self.dialog_values)
        else:  # add event to obs
            filename = self._set.add_event(self.selected_obs.id, self.dialog_values)

        # update observation_table
        if self.observation_table():
            self.observation_table().refresh_model()
        else:
            self.parent().parent().refresh_seek_bar()

        # save frame
        self.parent().save_image(filename)

        # close and clean up
        self.cleanup()

    def pushed_update(self):
        if self.action == DialogActions.edit_obs:
            self._set.edit_observation(self.selected_obs, self.dialog_values)
        else:
            self._set.edit_event(self.selected_event, self.dialog_values)

        # update observation_table
        self.observation_table().refresh_model()

        # close and clean up
        self.cleanup()

    def cleanup(self):
        self.dialog_values = {}
        self.action = None
        self.selected_obs = None
        self.selected_event = None
        self.close()
        self = None
        # self.parent().clear_extent()

    def attribute_select(self):
        # note that API is expecting singular "attribute" here, no "attributes"
        self.dialog_values['attribute'] = self.att_dropdown.get_selected_ids()

    def animal_select(self):
        self.dialog_values['animal_id'] = self.animal_dropdown.itemData(self.animal_dropdown.currentIndex())

    def note_change(self):
        self.dialog_values['note'] = self.text_area.toPlainText()

    def obs_note_change(self):
        self.dialog_values['comment'] = self.obs_text.toPlainText()

    def observation_table(self):
        try:
            return self.parent().parent()._observation_table
        except AttributeError:
            return None
