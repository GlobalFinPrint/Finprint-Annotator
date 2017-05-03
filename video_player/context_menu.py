from .attribute_selector import AttributeSelector
from annotation_view import TypeAndReduce
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from enum import IntEnum
from annotation_view.util import ObservationColumn
import re
from logging import getLogger

MARK_ZERO_TIME_ID = 16
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
        # set
        self._set = current_set
        if self._set is not None:
            self.setStyleSheet('QMenu::item:selected { background-color: lightblue; }')
            self._animal_observation_act = self.addAction('Create animal observation')
            self._interest_act = self.addAction('Create non-animal observation')
            self._observations_menu = self.addMenu('Add to existing observation')
            self._cancel_act = self.addAction('Cancel')

            if len(self._set.observations) == 0:
                self._observations_menu.menuAction().setVisible(False)
                self._animal_observation_act.setVisible(False)
                self._interest_act.setVisible(True)
                self._cancel_act.setVisible(False)
                getLogger('finprint').debug('ContextMenu : Mark Zero TIme is not created')
            else :
                self._observations_menu.menuAction().setVisible(True)
                self._animal_observation_act.setVisible(True)
                self._interest_act.setVisible(True)
                self._cancel_act.setVisible(True)


    def _populate_obs_menu(self):
        self.handle_annotator_event()
        self._set.observations.sort(key=lambda o: o.initial_time(), reverse=True)
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
        elif action == self._animal_observation_act :
            self.itemSelected.emit({"action": DialogActions.new_obs,
                                    "type_choice": 'A'})
        elif type(action.data()).__name__ == 'Observation':
            self.itemSelected.emit({"action": DialogActions.add_event,
                                    "obs": action.data()})


    def handle_annotator_event(self):
        if self._set is not None:
            if len(self._set.observations) > 0 :
                self._animal_observation_act.setVisible(True)
                self._interest_act.setVisible(True)
                self._observations_menu.menuAction().setVisible(True)
                self._cancel_act.setVisible(True)
            else :
                self._interest_act.setVisible(True)
                self._observations_menu.menuAction().setVisible(False)
                self._animal_observation_act.setVisible(False)
                self._cancel_act.setVisible(False)



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
        self.action = None
        self.column_name = None
        self._set = None

    def launch(self, kwargs):
        self.action = kwargs['action']
        if kwargs['action'] == DialogActions.new_obs:
            if  kwargs['type_choice']=='A':
               title = 'New animal observation'
            else:
               title = 'New non-animal observation'
        elif kwargs['action'] == DialogActions.add_event:
            if kwargs['obs'].type_choice == 'A':
                title ='Add event to animal observation'
            else :
                title = 'Add event to non-animal observation'
        elif kwargs['action'] == DialogActions.edit_obs:
            title = 'Edit animal observation'
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
            if kwargs['type_choice'] == 'I' :
                self.setWindowTitle("Edit non-animal observation")

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

        if 'obs' in kwargs :
            self.selected_event = kwargs['obs'].events
            self.dialog_values['note'] = self.selected_event[0].note
            self.dialog_values['attribute'] = [a['id'] for a in self.selected_event[0].attribute]
        # set up dialog view
        layout = QVBoxLayout()

        # adding highlight on the coloum on which it clicked
        if kwargs['action'] == DialogActions.edit_obs:
            column_details = ObservationColumn.return_observation_table_coloumn_details()
            if kwargs["column_number"] is not None :
              self.column_name = column_details[kwargs["column_number"]]

        if kwargs['action'] in [DialogActions.edit_obs, DialogActions.add_event]:
            obs_time_label = QLabel('Observation Time: '+str(self.selected_obs).split(" ")[0])
            layout.addWidget(obs_time_label)

        #adding grouping of Animal functionality in drop down of organism rather than showing animal list directly-GLOB-573
        if kwargs['action'] == DialogActions.edit_obs and kwargs['type_choice'] == 'A':
            animal_label = QLabel('Organism:')
            self.animal_dropdown = QComboBox()
            animal_label.setBuddy(self.animal_dropdown)
            for an in self._set.animals:
                self.animal_dropdown.addItem(str(an), an.id)
            self.animal_dropdown.setCurrentIndex(self.animal_dropdown.findData(self.dialog_values['animal_id']))
            self.animal_dropdown.currentIndexChanged.connect(self.animal_select)
            layout.addWidget(animal_label)
            layout.addWidget(self.animal_dropdown)

        # obs animal (if applicable)
        if kwargs['action'] in [DialogActions.new_obs] and kwargs['type_choice'] == 'A':
            animal_label = QLabel('Organism:')
            self.animal_dropdown = QComboBox()
            animal_label.setBuddy(self.animal_dropdown)
            for an in self._set.animals:
                self.animal_dropdown.addItem(str(an), an.id)

            self.dialog_values['animal_id'] = self.animal_dropdown.itemData(self.animal_dropdown.currentIndex())
            self.animal_dropdown.currentIndexChanged.connect(self.animal_select)
            layout.addWidget(animal_label)
            layout.addWidget(self.animal_dropdown)

        # attributes
        if kwargs['action'] != DialogActions.edit_obs:
            if len(self._set.observations) == 0 :
                self.dialog_values['attribute'] = [MARK_ZERO_TIME_ID]

            self.att_dropdown = AttributeSelector(self._set.attributes, self.dialog_values['attribute'])
            #changes for MARK ZERO TIME observation
            if len(self._set.observations) == 0:
                name_of_Mark_zero_time = [attr['verbose'] for attr in self._set.attributes if attr['id'] == MARK_ZERO_TIME_ID][0]
                self.att_dropdown.input_line.setText(name_of_Mark_zero_time)

            self.att_dropdown.selected_changed.connect(self.attribute_select)
            layout.addLayout(self.att_dropdown)

            # attributes added for edit observation
        if kwargs['action'] == DialogActions.edit_obs:
            self.att_dropdown = AttributeSelector(self._set.attributes, self.dialog_values['attribute'])
            if self.selected_obs.events and len(self.selected_obs.events[0].attribute)!=0:
                self.att_dropdown.on_select(self.selected_obs.events[0].attribute[0]["verbose"], True)

            self.att_dropdown.selected_changed.connect(self.attribute_select)
            layout.addLayout(self.att_dropdown)

        # observation notes
        if kwargs['action'] in [DialogActions.new_obs, DialogActions.edit_obs]:
            obs_notes_label = QLabel('Observation Note:')
            self.obs_text = QTextEdit()

            if 'obs' in kwargs:
                if kwargs['action'] == DialogActions.edit_obs and  self.column_name is not None and self.column_name == 'Observation Note' :
                    self.obs_text.setTextColor(QColor(Qt.red))
                    self.obs_text.setText(kwargs['obs'].comment)
                else :
                    self.obs_text.setPlainText(kwargs['obs'].comment)
            obs_notes_label.setBuddy(self.obs_text)
            self.obs_text.setFixedHeight(50)
            self.obs_text.textChanged.connect(self.obs_note_change)
            layout.addWidget(obs_notes_label)
            layout.addWidget(self.obs_text)

        # event notes
        if kwargs['action'] in [DialogActions.edit_obs,DialogActions.new_obs, DialogActions.add_event] :
            notes_label = QLabel('Image notes:')
            self.text_area = QTextEdit()
            if self.column_name is not None and self.column_name == 'Image notes':
                self.text_area.setTextColor(QColor(Qt.red))
                self.text_area.setText(self.dialog_values['note'])
            else :
                self.text_area.setText(self.dialog_values['note'])
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
            self._set.edit_event(self.selected_event[0], self.dialog_values)
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
        if len(self._set.observations) > 0:
            self.dialog_values['attribute'] = self.att_dropdown.get_selected_ids()
        else :
            msg = 'Create Mark Zero Observation first!!'
            QMessageBox.question(self, 'Delete confirmation', msg, QMessageBox.Close)
            self.dialog_values['attribute'] = [MARK_ZERO_TIME_ID]

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

    def show_nested_drop_down_for_organism(self)  :
        change_organism_menu = QMenu(self)
        grouping = {}
        for animal in self._set.animals:
            if animal.group not in grouping:
                grouping[animal.group] = []
            grouping[animal.group].append(animal)
        for group in grouping.keys():
            group_menu = change_organism_menu.addMenu(group)
            for animal in grouping[group]:
                act = group_menu.addAction(str(animal))
                act.setData(animal)
