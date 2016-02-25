import sys
import logging
import logging.config

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from pydispatch import dispatcher

from annotation_view import VideoLayoutWidget
from global_finprint import GlobalFinPrintServer, Set

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self._login_layout = None
        self._vid_layout = None
        self._set_layout = None
        self._has_logged_in = False #if a successful log in has occurred, don't exit app when cancelling login dialog

        self.setWindowIcon(QIcon('./images/shark-icon.png'))
        self._init_widgets()

        dispatcher.connect(self.on_login, signal='LOGIN', sender=dispatcher.Any)
        dispatcher.connect(self.on_login_cancelled, signal='LOGIN_CANCELLED', sender=dispatcher.Any)
        dispatcher.connect(self.set_selected, signal='SET_SELECTED', sender=dispatcher.Any)

    def _init_widgets(self):
        self._set_menus()
        self.statusBar()

        self._vid_layout = VideoLayoutWidget()
        self.setCentralWidget(self._vid_layout)
        self.showMaximized()
        self._launch_login_dialog()

    def _set_menus(self):
        menubar = QMenuBar()
        fileMenu = menubar.addMenu('&File')

        if GlobalFinPrintServer().logged_in:
            logOutAction = QAction('Log&out', self)
            logOutAction.setShortcut('Ctrl+O')
            logOutAction.setStatusTip('Logout of GlobalFinprint')
            logOutAction.triggered.connect(self._logout)
            fileMenu.addAction(logOutAction)

            setListAction = QAction('Set &List...', self)
            setListAction.setShortcut('Ctrl+S')
            setListAction.setStatusTip('View Set Lists')
            setListAction.triggered.connect(self._launch_set_list)
            fileMenu.addAction(setListAction)
        else:
            logInAction = QAction('&Login', self)
            logInAction.setShortcut('Ctrl+L')
            logInAction.setStatusTip('Login to GlobalFinprint')
            logInAction.triggered.connect(self._launch_login_dialog)
            fileMenu.addAction(logInAction)

        exitAction = QAction(QIcon('exit.png'), '&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(QCoreApplication.instance().quit)
        fileMenu.addAction(exitAction)
        self.setMenuBar(menubar)

    # TODO: The login widget should just be the dialog
    def _launch_login_dialog(self):
        self._login_layout = QVBoxLayout()
        self._login_widget = LoginWidget()
        self._login_layout.addWidget(self._login_widget)
        self.login_diag = QDialog(self, Qt.WindowTitleHint)
        self.login_diag.setLayout(self._login_layout)
        self.login_diag.setModal(True)
        #self.login_diag.closeEvent = self.loginCloseEvent
        self.login_diag.setWindowTitle('Login to Global Finprint')
        self.login_diag.show()

    def loginCloseEvent(self, event):
        pass
        #dispatcher.send('LOGIN_CANCELLED', sender=dispatcher.Anonymous, value='')


    def _launch_set_list(self, sets=False):
        self._set_layout = QVBoxLayout()
        self._set_list = SetListWidget()

        if not sets:
            response = GlobalFinPrintServer().set_list()
            sets = response['sets']

        for s in sets:
            self._set_list.add_item(s)

        self._set_layout.addWidget(self._set_list)
        self.set_diag = QDialog(self, Qt.WindowTitleHint)
        self.set_diag.setLayout(self._set_layout)
        self.set_diag.setWindowTitle('Assigned Sets List')
        self.set_diag.show()

    def _logout(self):
        client = GlobalFinPrintServer()
        if client.logout():
            self._set_menus()
            self._vid_layout.clear()

    def on_login(self, signal, sender, value):
        self._has_logged_in = True
        self.login_diag.close()
        self._set_menus()
        self._launch_set_list(value)

    def on_login_cancelled(self, signal, sender, value):
        self.login_diag.close()
        #exit application if login box is cancelled before ever loggin in
        if not self._has_logged_in:
            QCoreApplication.instance().quit()

    def set_selected(self, signal, sender, value):
        self.set_diag.close()
        s = Set(value['id'])
        self._vid_layout.load_set(s)


class LoginWidget(QWidget):
    def __init__(self):
        super(LoginWidget, self).__init__()

        logo = QLabel()
        logo.setGeometry(100, 100, 130, 130)
        logo.setPixmap(QPixmap("./images/Fin-Print-Horizontal-Logo-5.png"))

        user = QLabel('User Name')
        pwd = QLabel('Password')

        self.user_edit = QLineEdit()
        self.user_edit.setMaximumWidth(300)

        self.pwd_edit = QLineEdit()
        self.pwd_edit.setMaximumWidth(300)
        self.pwd_edit.setEchoMode(QLineEdit.Password)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("QLabel {color:red;}")

        login_button = QPushButton('Login')
        login_button.clicked.connect(self._on_login)
        login_button.setMaximumWidth(50)
        login_button.autoDefault = True
        login_button.keyPressEvent = self._key_press

        cancel_button = QPushButton('Cancel')
        cancel_button.clicked.connect(self._login_cancel)
        cancel_button.setMaximumWidth(50)

        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignRight)
        button_layout.addWidget(login_button)
        button_layout.addWidget(cancel_button)

        form = QFormLayout()

        form.addRow(logo)
        form.addRow('User Name', self.user_edit)
        form.addRow('Password', self.pwd_edit)
        form.addWidget(self.error_label)
        form.addRow(button_layout)
        #form.addWidget(login_button)
        #form.addWidget(cancel_button)

        grid = QGridLayout()
        grid.addLayout(form, 40, 40)

        self.setLayout(grid)

        self.setWindowTitle('User Login')
        self.setGeometry(100, 100, 200, 100)


    def _on_login(self):
        self.error_label.setText('')

        try:
            client = GlobalFinPrintServer()
            (success, data) = client.login(user_name=self.user_edit.text(), pwd=self.pwd_edit.text())
        except Exception as ex:
            success = False
            data = {'msg': 'Failed to connect to Server'}

        if success:
            dispatcher.send('LOGIN', sender=dispatcher.Anonymous, value=data['sets'])
        else:
            logging.getLogger("Finprint").error("Login Failed: " + data['msg'])
            self.error_label.setText(data['msg'])

    def _key_press(self, e):
        if e.key() == Qt.Key_Enter:
            self._on_login()

    def _login_cancel(self):
        dispatcher.send('LOGIN_CANCELLED', sender=dispatcher.Anonymous, value='')


class SetListWidget(QWidget):

    def __init__(self):
        super(SetListWidget, self).__init__()

        self.set_list = QListWidget()
        self.set_list.setMinimumSize(600, 400)
        self.set_list.setFont(self._get_font())
        self.set_list.setSelectionMode(QAbstractItemView.SingleSelection)

        self.set_list.doubleClicked.connect(self.on_list_item_clicked)
        self.list_container = QVBoxLayout()
        self.list_container.addWidget(self.set_list)

        self.setLayout(self.list_container)

    def add_item(self, set):
        i = QListWidgetItem()
        i.setText(set['set_code'])
        i.setData(Qt.UserRole, set)
        self.set_list.addItem(i)

    def _get_font(self):
        font = QFont()
        font.setPointSize(14)
        return font

    def on_list_item_clicked(self, index):
        dispatcher.send('SET_SELECTED', dispatcher.Anonymous, value=self.set_list.currentItem().data(Qt.UserRole))


def main():
    logging.config.fileConfig('./config.ini')
    l = logging.getLogger('finprint')
    l.info('Finprint Annotator Starting up')
    app = QApplication(sys.argv)
    app.setStyle("Plastique")
    win = MainWindow()
    win.setWindowTitle('Finprint Annotator')
    win.show()
    win.activateWindow()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()