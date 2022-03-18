from PyQt5              import QtWidgets
from mymoneyman.widgets import accounts

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self._initWidgets()
    
    def _initWidgets(self):
        self._pages = QtWidgets.QTabWidget()
        self._pages.addTab(accounts.AccountPage(), 'Accounts')

        self.setCentralWidget(self._pages)