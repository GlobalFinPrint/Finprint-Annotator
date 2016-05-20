import sys
import logging
import logging.config
from finprint_annotator import MainWindow
from PyQt4.QtGui import *


def main():
    logging.config.fileConfig('./config.ini')
    l = logging.getLogger('finprint')
    l.info('Finprint Annotator Starting up')
    app = QApplication(sys.argv)
    app.setStyle("Plastique")
    win = MainWindow()
    win.show()
    win.activateWindow()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
