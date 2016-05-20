import logging
from pydispatch import dispatcher
from global_finprint import GlobalFinPrintServer
from PyQt4.QtGui import *
from PyQt4.QtCore import *


class LoginWidget(QWidget):
    def __init__(self):
        super(LoginWidget, self).__init__()

        logo = QLabel()
        logo.setGeometry(100, 100, 130, 130)
        logo.setPixmap(QPixmap("./images/logo.png"))

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
