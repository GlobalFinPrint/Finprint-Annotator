from PyQt4.QtCore import *
from PyQt4.QtGui import *

class MultiKeyPressHandler:

    def handle_keyboard_shortcut_event(self, evt, filter_widget):
        '''
        Considering that keyboard shortcut in windows
        as per explained is ,anything which involves shift modifier
        or control modifier or both or F1 keyPress.
        '''
        if evt.key() in [Qt.Key_F1, Qt.Key_Escape]:
            filter_widget.hide()
            return True
        elif evt.modifiers() & Qt.ShiftModifier :
            filter_widget.hide()
            return True
        elif evt.modifiers() & Qt.ControlModifier :
            filter_widget.hide()
            return True
        elif evt.modifiers() & Qt.ShiftModifier and evt.modifiers() & Qt.ControlModifier :
            filter_widget.hide()
            return True

        return False