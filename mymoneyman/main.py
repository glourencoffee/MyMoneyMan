import sys, logging
from PyQt5      import QtWidgets
from mymoneyman import resources, widgets

def main():
    logging.basicConfig(level=logging.DEBUG)

    app = QtWidgets.QApplication(sys.argv)
    win = widgets.MainWindow()
    win.resize(800, 600)
    win.show()

    try:
        filepath = sys.argv[1]
        win.setFileEngine(filepath)
    except IndexError:
        pass

    return app.exec()

if __name__ == '__main__':
    sys.exit(main())