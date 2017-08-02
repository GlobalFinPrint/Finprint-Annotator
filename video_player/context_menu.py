from .attribute_selector import AttributeSelector
from annotation_view import TypeAndReduce
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from enum import IntEnum
from annotation_view.util import ObservationColumn
from global_finprint.global_finprint_server import GlobalFinPrintServer
from threading import Thread
import re
from logging import getLogger

DEFAULT_ATTRIBUTE_TAG = '-- search for a tag or use down arrow to see full list --'
MARK_ZERO_TIME_ID = 16
MAXN_IMAGE_FRAME_ID = 13


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
        # animals
        if self._set is not None:
            self.setStyleSheet('QMenu::item:selected { background-color: lightblue; }')
            self._grouping = {}
            for animal in self._set.animals:
                if animal.group not in self._grouping:
                    self._grouping[animal.group] = []
                self._grouping[animal.group].append(animal)

            # actions
            self._animal_group_menu = self.addMenu('Create animal observation')
            for group in sorted(self._grouping.keys()):
                group_menu = self._animal_group_menu.addMenu(group)
                group_menu.addAction(TypeAndReduce(group, self._grouping[group], self._debug, group_menu))

            self._interest_act = self.addAction('Create non-animal observation')
            self._observations_menu = self.addMenu('Add to existing observation')
            self._cancel_act = self.addAction('Cancel')
            if len(self._set.observations) == 0 and not GlobalFinPrintServer().is_lead():
                self._observations_menu.menuAction().setEnabled(False)
                self._animal_group_menu.menuAction().setEnabled(False)
                getLogger('finprint').debug('ContextMenu : Mark Zero TIme is not created')
            else:
                self._observations_menu.menuAction().setEnabled(True)
                self._animal_group_menu.menuAction().setEnabled(True)

    def _populate_obs_menu(self):
        self._observations_menu.clear()
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
        elif type(action.data()).__name__ == 'Observation':
            self.itemSelected.emit({"action": DialogActions.add_event,
                                    "obs": action.data()})

    def handle_annotator_event(self):
        if self._set is not None:
            if len(self._set.observations) > 0 or GlobalFinPrintServer().is_lead():
                self._animal_group_menu.menuAction().setEnabled(True)
                self._observations_menu.menuAction().setEnabled(True)
            else:
                self._observations_menu.menuAction().setEnabled(False)
                self._animal_group_menu.menuAction().setEnabled(False)

    def _debug(self, item):
        self.itemSelected.emit({"action": DialogActions.new_obs,
                                "type_choice": 'A',
                                "animal": item.choice})


class EventDialog(QDialog):
    itemSelected = pyqtSignal(dict)

    def __init__(self, parent=None, flags=Qt.WindowTitleHint):
        super(EventDialog, self).__init__(parent=parent, flags=flags)

        self.setFixedWidth(300)  # TODO bigger for tag selector?
        self.setModal(True)
        self.setStyleSheet('background:#fff;')
        self.finished.connect(self.cleanup)
        self.cascaded_menu = None

        # event params
        self.dialog_values = {}
        self.cursor_click_pos = None

        # dialog controls
        self.att_dropdown = None
        self.animal_dropdown = None
        self.text_area = None
        self.obs_text = None
        self.selected_obs = None
        self.selected_event = None
        self.action = None
        self.column_name = None
        self.row_number = None
        self.selected_evt = None
        self._set = None
        self.capture_video_check = None

    def launch(self, kwargs):
        self.action = kwargs['action']
        if kwargs['action'] == DialogActions.new_obs:
            if kwargs['type_choice'] == 'A':
                title = 'New animal observation'
            else:
                title = 'New non-animal observation'
        elif kwargs['action'] == DialogActions.add_event:
            if kwargs['obs'].type_choice == 'A':
                title = 'Add event to animal observation'
            else:
                title = 'Add event to non-animal observation'
        elif kwargs['action'] == DialogActions.edit_obs:
            if kwargs['obs'].type_choice == 'A':
                title = 'Edit animal observation'
            else:
                title = 'Edit non-animal observation'
        elif kwargs['action'] == DialogActions.edit_event:
            title = 'Edit event'
        else:
            title = ''  # should never happen
        self.setWindowTitle(title)

        self.dialog_values['note'] = ''
        self.dialog_values['attribute'] = None
        self.dialog_values['measurables'] = None
        self._set = kwargs['set']

        if 'row_number' in kwargs:
            self.row_number = kwargs['row_number']

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

        if 'obs' in kwargs:
            self.selected_event = kwargs['obs'].events
            self.dialog_values['note'] = self.selected_event[0].note
            self.dialog_values['attribute'] = [a['id'] for a in self.selected_event[0].attribute]
        # set up dialog view
        layout = QVBoxLayout()

        # adding highlight on the coloum on which it clicked
        if kwargs['action'] == DialogActions.edit_obs:
            column_details = ObservationColumn.return_observation_table_coloumn_details()
            if kwargs["column_number"] is not None:
                self.column_name = column_details[kwargs["column_number"]]
                self.selected_evt = self.find_event_to_update()

        if kwargs['action'] in [DialogActions.edit_obs, DialogActions.add_event]:
            obs_time_label = QLabel('Observation Time: ' + str(self.selected_obs).split(" ")[0])
            layout.addWidget(obs_time_label)

        # adding grouping of Animal functionality in drop down of organism rather than showing animal list directly-GLOB-573
        if kwargs['action'] == DialogActions.edit_obs and kwargs['type_choice'] == 'A':
            animal_label = QLabel('Organism:*')
            self.animal_dropdown = ComboBox(self)
            animal_label.setBuddy(self.animal_dropdown)
            for an in self._set.animals:
                self.animal_dropdown.addItem(str(an), an.id)
            self.animal_dropdown.setCurrentIndex(self.animal_dropdown.findData(self.dialog_values['animal_id']))
            self.animal_dropdown.popupAboutToBeShown.connect(self.cascaded_drop_down)

            layout.addWidget(animal_label)
            layout.addWidget(self.animal_dropdown)

        # obs animal (if applicable)
        if kwargs['action'] in [DialogActions.new_obs] and kwargs['type_choice'] == 'A':
            animal_label = QLabel('Organism:*')
            self.animal_dropdown = QComboBox()
            animal_label.setBuddy(self.animal_dropdown)
            for an in self._set.animals:
                self.animal_dropdown.addItem(str(an), an.id)

            self.animal_dropdown.setCurrentIndex(self.animal_dropdown.findData(self.dialog_values['animal_id']))
            self.animal_dropdown.currentIndexChanged.connect(self.animal_select)
            layout.addWidget(animal_label)
            layout.addWidget(self.animal_dropdown)

        # MaxN addition
        if kwargs['type_choice'] == 'A':
            self.max_n_value = QLineEdit()
            self.max_n_value.setValidator(QIntValidator())
            self.max_n_value.setMaximumWidth(40)
            self.max_n_value.setMaxLength(2)
            self.max_n_value.setAlignment(Qt.AlignLeft)
            max_n_label = QFormLayout()
            max_n_label.addRow('MaxN:', self.max_n_value)
            layout.addLayout(max_n_label)

        # attributes
        if kwargs['action'] != DialogActions.edit_obs:
            if len(self._set.observations) == 0 and not GlobalFinPrintServer().is_lead():
                self.dialog_values['attribute'] = [MARK_ZERO_TIME_ID]

            self.att_dropdown = AttributeSelector(self._set.attributes, self.dialog_values['attribute'],
                                                  self._set.observations)
            # changes for MARK ZERO TIME observation
            if len(self._set.observations) == 0 and not GlobalFinPrintServer().is_lead():
                list_att_containing_mark_zero = [attr['verbose'] for attr in self._set.attributes if
                                                 attr['id'] == MARK_ZERO_TIME_ID]
                if list_att_containing_mark_zero:
                    name_of_Mark_zero_time = list_att_containing_mark_zero[0]
                    self.att_dropdown.input_line.setText(DEFAULT_ATTRIBUTE_TAG)
                else:
                    self.att_dropdown.input_line.setText('MARK ZERO TIME')
            else:
                self.att_dropdown.on_select(DEFAULT_ATTRIBUTE_TAG)

            self.att_dropdown.selected_changed.connect(self.attribute_select)
            layout.addLayout(self.att_dropdown)

        # attributes added for edit observation
        if kwargs['action'] == DialogActions.edit_obs:
            self.att_dropdown = AttributeSelector(self._set.attributes, self.dialog_values['attribute'],
                                                  self._set.observations)
            if len(self.dialog_values['attribute']) != 0:
                for attr in self._set.attributes:
                    if attr['id'] in self.dialog_values['attribute']:
                        self.att_dropdown.on_select(attr['verbose'], True)
                    elif 'children' in attr:
                        for child in attr['children']:
                            if child['id'] in self.dialog_values['attribute']:
                                self.att_dropdown.on_select(child['verbose'], True)

            if self.dialog_values['attribute'] is None or len(self.dialog_values['attribute']) == 0:
                self.att_dropdown.on_select(DEFAULT_ATTRIBUTE_TAG)

            self.att_dropdown.selected_changed.connect(self.attribute_select)
            layout.addLayout(self.att_dropdown)

        # observation notes
        if kwargs['action'] in [DialogActions.new_obs, DialogActions.edit_obs]:
            obs_notes_label = QLabel('Observation Note:')
            self.obs_text = QTextEdit()

            if 'obs' in kwargs:
                if kwargs[
                    'action'] == DialogActions.edit_obs and self.column_name is not None and self.column_name == 'Observation Note':
                    self.obs_text.setTextColor(QColor(Qt.red))
                    self.obs_text.setText(kwargs['obs'].comment)
                else:
                    self.obs_text.setPlainText(kwargs['obs'].comment)
            obs_notes_label.setBuddy(self.obs_text)
            self.obs_text.setFixedHeight(50)
            self.obs_text.textChanged.connect(self.obs_note_change)
            layout.addWidget(obs_notes_label)
            layout.addWidget(self.obs_text)

        # event notes
        if kwargs['action'] in [DialogActions.edit_obs, DialogActions.new_obs, DialogActions.add_event]:
            notes_label = QLabel('Image notes:')
            self.text_area = QTextEdit()
            if self.column_name is not None and self.column_name == 'Image notes':
                self.text_area.setTextColor(QColor(Qt.red))
                self.text_area.setText(self.dialog_values['note'])
            else:
                self.text_area.setText(self.dialog_values['note'])
            notes_label.setBuddy(self.text_area)
            self.text_area.setFixedHeight(50)
            self.text_area.textChanged.connect(self.note_change)
            layout.addWidget(notes_label)
            layout.addWidget(self.text_area)

        if kwargs['action'] in [DialogActions.edit_obs, DialogActions.new_obs, DialogActions.add_event]:
            self.capture_video_check = QCheckBox("Capture video")
            layout.addWidget(self.capture_video_check)

        last_row = QHBoxLayout()
        # *required field note
        asterick_note = QLabel('* Required field')
        last_row.addWidget(asterick_note)

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
        last_row.addWidget(buttons)
        layout.addLayout(last_row)
        self.setLayout(layout)
        if self.column_name is not None and self.column_name == 'Image notes':
            self.text_area.setFocus()
        if self.column_name is not None and self.column_name == 'Observation Note':
            self.obs_text.setFocus()
        if self.column_name is not None and self.column_name == 'Organism' and kwargs['type_choice'] == 'A':
            self.animal_dropdown.setStyleSheet("QComboBox { border: 2px solid #72aaff; } ")
            self.animal_dropdown.setFocus()
        if self.column_name is not None and self.column_name == 'Tags' or kwargs['action'] == DialogActions.new_obs:
            self.att_dropdown.input_line.setFocus()

        self.show()

    def pushed_save(self):
        if self.dialog_values['attribute'] is not None and -1 in self.dialog_values['attribute']:
            self.dialog_values['attribute'].remove(-1)

        if len(self._set.observations) == 0 and not GlobalFinPrintServer().is_lead():
            self._set.progress = self.dialog_values['event_time']
            GlobalFinPrintServer().update_progress(self._set.id, self.dialog_values['event_time'])

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

        # save 8_sec_clip
        if self.capture_video_check is not None and self.capture_video_check.isChecked() == True:
            file_name = re.split(".png", filename)[0] + ".mp4"
            thread = Thread(target=self.upload_8sec_clip, args=(file_name,))
            thread.start()

        # close and clean up
        self.cleanup()

    def pushed_update(self):
        # added for default tag
        if self.dialog_values['attribute'] is not None and -1 in self.dialog_values['attribute']:
            self.dialog_values['attribute'].remove(-1)
        if self.action == DialogActions.edit_obs:
            filename = self._set.edit_observation(self.selected_obs, self.dialog_values)
            if self.selected_evt is not None:
                selected_evt = [child_event for child_event in self.selected_obs.events if
                                child_event.id == self.selected_evt['event_id']][0]
                filename = self._set.edit_event(selected_evt, self.dialog_values)
        else:
            self._set.edit_event(self.selected_event, self.dialog_values)
        # update observation_table
        self.observation_table().refresh_model()

        # save 8_sec_clip
        if self.capture_video_check.isChecked() == True:
            file_name = re.split(".png", filename)[0] + ".mp4"
            thread = Thread(target=self.upload_8sec_clip, args=(file_name,))
            thread.start()
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
        self.dialog_values['attribute'] = self.att_dropdown.get_selected_ids()
        if MARK_ZERO_TIME_ID not in self.dialog_values['attribute'] and len(
                self._set.observations) == 0 and not GlobalFinPrintServer().is_lead():
            msg = 'You must create a MARK ZERO TIME observation first'
            QMessageBox.question(self, 'MARK ZERO OBSERVATION', msg, QMessageBox.Close)
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

    def cascaded_drop_down(self):
        stylesheet = self.setStyleSheet('QMenu::item:selected { background-color: lightblue; }')
        self.cascaded_menu = QMenu(self)
        self.cascaded_menu.setStyleSheet(stylesheet)
        self.cascaded_menu.setFixedWidth(300)
        self._grouping = {}
        for animal in self._set.animals:
            if animal.group not in self._grouping:
                self._grouping[animal.group] = []
            self._grouping[animal.group].append(animal)

            # actions
        # self._animal_group_menu = menu.addMenu('Create animal observation')
        for group in sorted(self._grouping.keys()):
            group_menu = self.cascaded_menu.addMenu(group)
            group_menu.addAction(TypeAndReduce(group, self._grouping[group], self._debug, group_menu, False))

            # self.display()
        x = self.pos().x() + self.animal_dropdown.x()
        y = self.pos().y() + self.animal_dropdown.y() + 28  # adjustment might change if more Qwidgets are added in layout

        self.cascaded_menu.move(x, y)
        self.animal_dropdown.setStyleSheet("QComboBox { background-color: white; }")
        self.cascaded_menu.show()

    def _debug(self, item):
        self.animal_dropdown.setCurrentIndex(self.animal_dropdown.findData(item.choice.id))
        self.dialog_values['animal_id'] = item.choice.id
        self.cascaded_menu.hide()

    def upload_8sec_clip(self, file_name):
        self.parent().generate_8sec_clip(file_name)

    def find_event_to_update(self):
        obs = sorted(self._set.observations, key=lambda o: o.initial_time())
        count = -1
        for o in reversed(obs):
            events = sorted(o.events, key=lambda e: e.event_time)
            for e in reversed(events):
                if count + 1 == self.row_number:
                    self.dialog_values['note'] = e.note
                    if e.observation.comment != None:
                        self.dialog_values['comment'] = e.observation.comment
                    else:
                        self.dialog_values['comment'] = ""

                    self.dialog_values['attribute'] = [attr['id'] for attr in e.attribute]

                    return {"event_id": e.id, "obs_id": o.id}
                else:
                    count = count + 1

    def mousePressEvent(self, *args, **kwargs):
        _list_of_tags = []
        if self.max_n_value.text():
            self.dialog_values['measurables'] = [int(self.max_n_value.text())]
            for attr in self._set.attributes:
                if 'children' in attr:
                    for child in attr['children']:
                        if child['id'] == MAXN_IMAGE_FRAME_ID:
                            _list_of_tags.append(child['verbose'])
                else:
                    if attr['id'] == MAXN_IMAGE_FRAME_ID:
                        _list_of_tags.append(attr['verbose'])

            if _list_of_tags:
                self.att_dropdown.on_select(_list_of_tags[0])
            else:
                self.att_dropdown.on_select(DEFAULT_ATTRIBUTE_TAG)
        else:
            self.att_dropdown.on_select(DEFAULT_ATTRIBUTE_TAG)


class ComboBox(QComboBox):
    popupAboutToBeShown = pyqtSignal()

    def showPopup(self):
        self.popupAboutToBeShown.emit()
