from PyQt5              import QtCore, QtWidgets
from mymoneyman.widgets import accounts, transactions, assets

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self._initWidgets()
    
    def _initWidgets(self):
        self._account_page = accounts.AccountPage()
        self._account_page.accountCreated.connect(self._onAccountCreated)
        self._account_page.accountDeleted.connect(self._onAccountDeleted)
        self._account_page.accountEdited.connect(self._onAccountEdited)
        self._account_page.accountDoubleClicked.connect(self._onAccountDoubleClicked)

        self._transaction_page = transactions.TransactionPage()

        self._currency_page = assets.CurrencyPage()

        #TODO: tr()
        self._pages = QtWidgets.QTabWidget()
        self._pages.addTab(self._account_page,     'Accounts')
        self._pages.addTab(self._transaction_page, 'Transactions')
        self._pages.addTab(self._currency_page,    'Currencies')

        self.setCentralWidget(self._pages)

    @QtCore.pyqtSlot(int)
    def _onAccountCreated(self, account_id: int):
        self._transaction_page.refresh()
    
    @QtCore.pyqtSlot(int)
    def _onAccountDeleted(self, account_id: int):
        self._transaction_page.refresh()
    
    @QtCore.pyqtSlot(int)
    def _onAccountEdited(self, account_id: int):
        self._transaction_page.refresh()

    @QtCore.pyqtSlot(int)
    def _onAccountDoubleClicked(self, account_id: int):
        self._transaction_page.selectAccount(account_id)
        self._pages.setCurrentWidget(self._transaction_page)