from PyQt4.QtCore import *

class MultiKeyPressHandler:

    def aggregate_key_event(self, key_pressed):
        return sum(key_pressed)

    def process_multi_key_press(self, obj):
        '''
        Handles event based on multi key press
        both for full screen and normal screen
        '''
        aggregate_key_events = self.aggregate_key_event(obj.keylist)
        if aggregate_key_events == Qt.Key_Shift + Qt.Key_Left:
            obj.on_step_back()
        elif aggregate_key_events == Qt.Key_Shift + Qt.Key_Right:
            obj.on_step_forward()
        elif aggregate_key_events == Qt.Key_Control + Qt.Key_Left:
            obj.on_back05()
        elif aggregate_key_events == Qt.Key_Control + Qt.Key_Down:
            obj.on_back15()

    def handle_keyboard_shortcut_event(self, evt, filter_widget):
        '''
        Considering that keyboard shortcut in windows
        as per explained is ,anything which involves shift modifier
        or control modifier or both or F1 keyPress.
        '''
        if evt.key() in [Qt.Key_F1, Qt.Key_Escape]:
            filter_widget.hide()
        if evt.modifiers() & Qt.ShiftModifier :
            filter_widget.hide()
        elif evt.modifiers() & Qt.ControlModifier :
            filter_widget.hide()
        elif evt.modifiers() & Qt.ShiftModifier and evt.modifiers() & Qt.ControlModifier :
            filter_widget.hide()