import sys
import os
import platform
import logging
import logging.config
from finprint_annotator import MainWindow
from PyQt4.QtGui import *


def main():
    # Get the base directory and the certificates directory for requests
    if getattr(sys, 'frozen', None):
        basedir = os.path.dirname(sys.executable)
        certdir = basedir
    else:
        basedir = os.path.dirname(__file__)
        basedir = os.path.normpath(basedir)
        certdir = os.path.join(basedir, 'requests')

    # Allows the requests library to find the certificates bundle
    os.environ['REQUESTS_CA_BUNDLE'] = os.path.join(certdir, 'cacert.pem')

    logging.config.fileConfig('./config.ini')
    l = logging.getLogger('finprint')
    l.info('Finprint Annotator Starting up')
    l.debug('Platform: {}'.format(platform.uname()))
    app = QApplication(sys.argv)
    app.setStyle("Plastique")
    win = MainWindow()
    win.show()
    win.activateWindow()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
