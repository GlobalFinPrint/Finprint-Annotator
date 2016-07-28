import itertools
import config
from pydispatch import dispatcher
from annotation_view import VideoLayoutWidget
from global_finprint import GlobalFinPrintServer, Set
from .login_widget import LoginWidget
from .assignment_widget import AssignmentWidget
from PyQt4.QtGui import *
from PyQt4.QtCore import *


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self._login_layout = None
        self._vid_layout = None
        self._set_layout = None
        self._props_layout = None
        self._has_logged_in = False  # if a successful log in has occurred, don't exit app when cancelling login dialog
        self.set_diag = None
        self.filter_diag = None

        self.setWindowIcon(QIcon('./images/shark-icon.png'))
        self.setWindowTitle('Finprint Annotator {0}'.format(config.__version_string__))
        self.setStyleSheet('background-color: white;')
        self._init_widgets()

        dispatcher.connect(self.on_login, signal='LOGIN', sender=dispatcher.Any)
        dispatcher.connect(self.on_login_cancelled, signal='LOGIN_CANCELLED', sender=dispatcher.Any)
        dispatcher.connect(self.set_selected, signal='SET_SELECTED', sender=dispatcher.Any)

    def _init_widgets(self):
        self.statusBar()
        self._vid_layout = VideoLayoutWidget(self)
        self._set_menus()
        self.setCentralWidget(self._vid_layout)
        self.showMaximized()  # TODO adjust this?
        self._launch_login_dialog()

    def _set_menus(self):
        menubar = QMenuBar()
        menubar.setStyleSheet("""QMenu::item:selected { background-color: lightblue; }
                                QMenuBar { border-bottom: 1px ridge black; }""")
        fileMenu = menubar.addMenu('&File')

        if GlobalFinPrintServer().logged_in:
            setListAction = QAction('Assigned Set &List...', self)
            setListAction.setShortcut('Ctrl+L')
            setListAction.setStatusTip('View list of assigned sets')  # TODO for lead default to self-assigned sets?
            setListAction.triggered.connect(self._launch_assign_diag)
            fileMenu.addAction(setListAction)

            if GlobalFinPrintServer().is_lead():
                setFilterAction = QAction('&Filter Review Sets...', self)
                setFilterAction.setShortcut('Ctrl+F')
                setFilterAction.setStatusTip('Filter sets for lead review')
                setFilterAction.triggered.connect(self._launch_assign_diag)
                fileMenu.addAction(setFilterAction)
        else:
            logInAction = QAction('&Login', self)
            logInAction.setShortcut('Ctrl+L')
            logInAction.setStatusTip('Login to GlobalFinprint')
            logInAction.triggered.connect(self._launch_login_dialog)
            fileMenu.addAction(logInAction)

        propsAction = QAction('&Properties...', self)
        propsAction.setShortcut('Ctrl+P')
        propsAction.setStatusTip('Edit application properties')
        propsAction.triggered.connect(self._launch_props_dialog)
        fileMenu.addAction(propsAction)

        quitAction = QAction('&Quit', self)
        quitAction.setShortcut('Ctrl+Q')
        quitAction.setStatusTip('Quit application')
        quitAction.triggered.connect(self._vid_layout.on_quit)
        fileMenu.addAction(quitAction)

        self.setMenuBar(menubar)

    # TODO: The login widget should just be the dialog
    def _launch_login_dialog(self):
        self._login_layout = QVBoxLayout()
        self._login_widget = LoginWidget()
        self._login_layout.addWidget(self._login_widget)
        self.login_diag = QDialog(self, Qt.WindowTitleHint)
        self.login_diag.setLayout(self._login_layout)
        self.login_diag.setModal(True)
        # self.login_diag.closeEvent = self.loginCloseEvent
        self.login_diag.setWindowTitle('Login to Global Finprint')
        self.login_diag.show()

    def loginCloseEvent(self, event):
        pass
        # dispatcher.send('LOGIN_CANCELLED', sender=dispatcher.Anonymous, value='')

    def _launch_props_dialog(self):
        self._props_layout = QVBoxLayout()

        self.props_diag = QDialog(self, Qt.WindowTitleHint)
        self.props_diag.setFixedWidth(500)
        self.props_diag.setWindowTitle('Edit properties')

        self.folder_finder = QHBoxLayout()

        self.source_label = QLabel('Video folder:')
        self.video_source = QLineEdit(config.global_config.get('VIDEOS', 'alt_media_dir'))

        self.find_folder = QPushButton('Browse...')
        self.find_folder.setMaximumSize(70, 35)
        self.find_folder.clicked.connect(self._browse_folder)

        self.source_label.setBuddy(self.video_source)
        self.video_source.setReadOnly(True)

        self.folder_finder.addWidget(self.source_label)
        self.folder_finder.addWidget(self.video_source)
        self.folder_finder.addWidget(self.find_folder)

        self.cancel_props = QPushButton('Cancel')
        self.cancel_props.clicked.connect(self._cancel_props_dialog)
        self.cancel_props.setMaximumSize(75, 35)
        self.save_props = QPushButton('Save')
        self.save_props.setMaximumSize(75, 35)
        self.save_props.clicked.connect(self._save_props_dialog)

        self.buttons = QDialogButtonBox(Qt.Horizontal)
        self.buttons.addButton(self.save_props, QDialogButtonBox.ActionRole)
        self.buttons.addButton(self.cancel_props, QDialogButtonBox.ActionRole)

        self._props_layout.addLayout(self.folder_finder)
        self._props_layout.addWidget(self.buttons)

        self.props_diag.setLayout(self._props_layout)
        self.props_diag.show()

    def _browse_folder(self):
        new_dir = QFileDialog.getExistingDirectory()
        if new_dir:
            self.video_source.setText(new_dir)

    def _cancel_props_dialog(self):
        self.props_diag.close()

    def _save_props_dialog(self):
        config.global_config.set_item('VIDEOS', 'alt_media_dir', self.video_source.text())
        self.props_diag.close()
        self._vid_layout.load_set(self._vid_layout.current_set)

    def _launch_assign_diag(self, sets=False):
        if sets is False:
            response = GlobalFinPrintServer().set_list(filtered=True)
            sets = response['sets']

        assign_layout = QVBoxLayout()
        assign_layout.addWidget(AssignmentWidget(sets))
        self.assign_diag = QDialog(self)
        self.assign_diag.setLayout(assign_layout)
        self.assign_diag.show()

    def on_login(self, signal, sender, value):
        self._has_logged_in = True
        self.login_diag.close()
        self._set_menus()
        self._launch_assign_diag(value)

    def on_login_cancelled(self, signal, sender, value):
        self.login_diag.close()
        # exit application if login box is cancelled before ever logging in
        if not self._has_logged_in:
            QCoreApplication.instance().quit()

    def set_selected(self, signal, sender, value):
        self.assign_diag.close()
        s = Set(value)
        self._vid_layout.load_set(s)
