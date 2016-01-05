import sys
from datetime import datetime, time
from math import floor
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from pydispatch import dispatcher

from annotation_view import VideoLayoutWidget


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

        #self.setGeometry(300, 300, 300, 200)

        self._login_layout = LoginWidget()
        self.setCentralWidget(self._login_layout)

    def on_login(self, signal, sender, value):
        self._vid_layout = VideoLayoutWidget()
        self.setCentralWidget(self._vid_layout)
        self.showMaximized()

        self._set_layout = QVBoxLayout()
        self._set_list = SetListWidget()
        self._set_layout.addWidget(self._set_list)
        self.login_diag = QDialog()
        self.login_diag.setLayout(self._set_layout)
        self.login_diag.show()

    def set_selected(self, signal, sender, value):
        self.login_diag.close()
        self._vid_layout.load(value)


class LoginWidget(QWidget):
    def __init__(self):
        super(LoginWidget, self).__init__()

        logo = QLabel()
        logo.setGeometry(100, 100, 130, 130)
        logo.setPixmap(QPixmap("./images/Fin-Print-Horizontal-Logo-5.png"))

        user = QLabel('User Name')
        pwd = QLabel('Password')

        user_edit = QLineEdit()
        user_edit.setMaximumWidth(200)

        pwd_edit = QLineEdit()
        pwd_edit.setMaximumWidth(200)

        login_button = QPushButton('Login')
        login_button.clicked.connect(self._on_login)
        login_button.autoDefault = True
        login_button.keyPressEvent = self._key_press

        form = QFormLayout()
        #form.setSpacing(10)

        form.addRow('', logo)
        form.addRow('User Name', user_edit)
        form.addRow('Password', pwd_edit)
        form.addWidget(login_button)

        # form.addWidget(user, 1, 0)
        # form.addWidget(user_edit, 1, 1)
        #
        # form.addWidget(pwd, 2, 0)
        # form.addWidget(pwd_edit, 2, 1)

        grid = QGridLayout()
        grid.addLayout(form, 40, 40)

        self.setLayout(grid)

        self.setWindowTitle('User Login')
        self.setGeometry(100, 100, 200, 100)
        #self.show()

    def _on_login(self):
        dispatcher.send('LOGIN', sender=dispatcher.Anonymous, value='')

    def _key_press(self, e):
        if e.key() == Qt.Key_Enter:
            self._on_login()


class SetListWidget(QWidget):
    test_data = ['Belize', 'West Jamaica', 'Roatan']

    def __init__(self):
        super(SetListWidget, self).__init__()

        self.set_list = QListWidget()
        self.set_list.setWindowTitle('Assigned Sets List')
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
    app = QApplication(sys.argv)
    r = app.setStyle("Plastique")
    win = MainWindow()
    #win.showMaximized()
    win.setWindowTitle('Finprint Annotator')
    win.show()
    win.activateWindow()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()