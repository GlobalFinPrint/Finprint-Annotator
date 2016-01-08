import sys
import logging
import logging.config


from PyQt4.QtGui import *
from PyQt4.QtCore import *

from pydispatch import dispatcher

from annotation_view import VideoLayoutWidget
from global_finprint import GlobalFinPrintServer


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self._login_layout = None
        self._vid_layout = None
        self._set_layout = None

        self.setWindowIcon(QIcon('./images/shark-icon.png'))
        self._init_widgets()

        dispatcher.connect(self.on_login, signal='LOGIN', sender=dispatcher.Any)
        dispatcher.connect(self.set_selected, signal='SET_SELECTED', sender=dispatcher.Any)

    def _init_widgets(self):
        exitAction = QAction(QIcon('exit.png'), '&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(QCoreApplication.instance().quit)

        self.statusBar()

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(exitAction)

        self._vid_layout = VideoLayoutWidget()
        self.setCentralWidget(self._vid_layout)
        self.showMaximized()
        self._launch_login_dialog()

    def _launch_login_dialog(self):
        self._login_layout = QVBoxLayout()
        self._login_widget = LoginWidget()
        self._login_layout.addWidget(self._login_widget)
        self.login_diag = QDialog(self, Qt.WindowTitleHint)
        self.login_diag.setLayout(self._login_layout)
        self.login_diag.setModal(True)
        self.login_diag.setWindowTitle('Login to Global Finprint')
        self.login_diag.show()

    def _launch_set_list(self):
        self._set_layout = QVBoxLayout()
        self._set_list = SetListWidget()
        self._set_layout.addWidget(self._set_list)
        self.set_diag = QDialog(self, Qt.WindowTitleHint)
        self.set_diag.setLayout(self._set_layout)
        self.set_diag.setWindowTitle('Assigned Sets List')
        self.set_diag.show()

    def on_login(self, signal, sender, value):
        self.login_diag.close()
        self._launch_set_list()

    def set_selected(self, signal, sender, value):
        self.set_diag.close()
        self._vid_layout.load(value)


class LoginWidget(QWidget):
    def __init__(self):
        super(LoginWidget, self).__init__()

        logo = QLabel()
        logo.setGeometry(100, 100, 130, 130)
        logo.setPixmap(QPixmap("./images/Fin-Print-Horizontal-Logo-5.png"))

        user = QLabel('User Name')
        pwd = QLabel('Password')

        self.user_edit = QLineEdit()
        self.user_edit.setMaximumWidth(200)

        self.pwd_edit = QLineEdit()
        self.pwd_edit.setMaximumWidth(200)
        self.pwd_edit.setEchoMode(QLineEdit.Password)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("QLabel {color:red;}")

        login_button = QPushButton('Login')
        login_button.clicked.connect(self._on_login)
        login_button.autoDefault = True
        login_button.keyPressEvent = self._key_press

        form = QFormLayout()

        form.addRow('', logo)
        form.addRow('User Name', self.user_edit)
        form.addRow('Password', self.pwd_edit)
        form.addWidget(self.error_label)
        form.addWidget(login_button)

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
            data = {'msg': ex}

        if success:
            dispatcher.send('LOGIN', sender=dispatcher.Anonymous, value=data)
        else:
            logging.getLogger("Finprint").error("Login Failed: " + data['msg'])
            self.error_label.setText(data)

    def _key_press(self, e):
        if e.key() == Qt.Key_Enter:
                self._on_login()


class SetListWidget(QWidget):
    test_data = ['Belize', 'West Jamaica', 'Roatan']

    def __init__(self):
        super(SetListWidget, self).__init__()

        self.set_list = QListWidget()
        self.set_list.setMinimumSize(600, 400)
        self.set_list.setFont(self._get_font())
        self.set_list.setSelectionMode(QAbstractItemView.SingleSelection)

        self.add_test_items()

        self.set_list.doubleClicked.connect(self.on_list_item_clicked)
        self.list_container = QVBoxLayout()
        self.list_container.addWidget(self.set_list)

        self.setLayout(self.list_container)

    def add_test_items(self):
        i = QListWidgetItem()
        i.setText("Belize")
        i.setData(Qt.UserRole, "videos/sharkcut.avi")
        self.set_list.addItem(i)

        i = QListWidgetItem()
        i.setText("West Jamaica")
        i.setData(Qt.UserRole, "videos/stitched.avi")
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