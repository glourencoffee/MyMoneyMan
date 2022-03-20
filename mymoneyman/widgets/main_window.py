from PyQt5              import QtWidgets
from mymoneyman.widgets import accounts, transactions

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self._initWidgets()
    
    def _initWidgets(self):
        #TODO: tr()
        self._pages = QtWidgets.QTabWidget()
        self._pages.addTab(accounts.AccountPage(),         'Accounts')
        self._pages.addTab(transactions.TransactionPage(), 'Transactions')

        self.setCentralWidget(self._pages)