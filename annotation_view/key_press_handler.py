from PyQt4.QtCore import *

class MultiKeyPressHandler:

    def aggregate_key_event(self, key_pressed):
        return sum(key_pressed)

    def process_multi_key_press(self, obj):
        '''
        handles event based on multi key press
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