from PyQt4.QtCore import *
from PyQt4.QtGui import *

class MultiKeyPressHandler:

    def register_application_shortcut_key(self, layout_obj = None):
        step_back_shortcut = QAction(layout_obj)
        step_back_shortcut.setShortcut(QKeySequence("Shift+Left"))
        layout_obj.connect(step_back_shortcut, SIGNAL("activated()"), layout_obj.on_step_back)
        layout_obj.addAction(step_back_shortcut)
        step_forward_shortcut = QAction(layout_obj)
        step_forward_shortcut.setShortcut(QKeySequence("Shift+Right"))
        layout_obj.connect(step_forward_shortcut, SIGNAL("activated()"), layout_obj.on_step_forward)
        layout_obj.addAction(step_forward_shortcut)
        step_back_5sec_shortcut = QAction(layout_obj)
        step_back_5sec_shortcut.setShortcut(QKeySequence("Ctrl+Left"))
        layout_obj.connect(step_back_5sec_shortcut, SIGNAL("activated()"), layout_obj.on_back05)
        layout_obj.addAction(step_back_5sec_shortcut)
        step_back_15sec_shortcut = QAction(layout_obj)
        step_back_15sec_shortcut.setShortcut(QKeySequence("Ctrl+Down"))
        layout_obj.connect(step_back_15sec_shortcut, SIGNAL("activated()"), layout_obj.on_back15)
        layout_obj.addAction(step_back_15sec_shortcut)


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