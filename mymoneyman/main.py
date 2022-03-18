import sys
from PyQt5      import QtWidgets
from mymoneyman import resources, widgets

def main():
    app = QtWidgets.QApplication(sys.argv)
    win = widgets.MainWindow()
    win.resize(800, 600)
    win.show()

    return app.exec()

if __name__ == '__main__':
    sys.exit(main())