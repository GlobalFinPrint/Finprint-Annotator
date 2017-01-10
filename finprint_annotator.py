import sys
import os
import platform
import logging
import logging.config
from finprint_annotator import MainWindow
from global_finprint import ExceptionHandling
from PyQt4.QtGui import *


def main():
    try:
        1/0
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
        l.debug('Processor: {}'.format(platform.processor()))
        app = QApplication(sys.argv)
        app.setStyle("Plastique")
        win = MainWindow()
        win.show()
        win.activateWindow()
        sys.exit(app.exec_())

    except Exception as e:
        r = ExceptionHandling().log_error()
        if r is None or r.status_code != 200:
            logging.getLogger('finprint').warning('Unable to log error to complaint box')
        raise e

if __name__ == '__main__':
    main()
