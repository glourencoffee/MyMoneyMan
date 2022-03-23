import typing
from PyQt5              import QtCore, QtGui, QtWidgets
from mymoneyman         import models
from mymoneyman.widgets import transactions as widgets, common

class TransactionPage(QtWidgets.QWidget):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._initWidgets()
        self._initLayouts()
    
    def _initWidgets(self):
        self._acc_selection_combo = common.AccountBox()
        self._acc_selection_combo.populate()
        self._acc_selection_combo.currentAccountChanged.connect(self._onCurrentAccountChanged)

        self._insert_transaction_btn = QtWidgets.QPushButton(QtGui.QIcon(':/icons/insert.png'), 'Insert transaction')
        self._remove_transaction_btn = QtWidgets.QPushButton(QtGui.QIcon(':/icons/delete.png'), 'Remove transaction')
        self._cancel_transaction_btn = QtWidgets.QPushButton(QtGui.QIcon(':/icons/cancel.png'), 'Cancel transaction')

        self._insert_transaction_btn.clicked.connect(self._onInsertTransactionButtonClicked)
        self._remove_transaction_btn.clicked.connect(self._onRemoveTransactionButtonClicked)
        self._cancel_transaction_btn.clicked.connect(self._onCancelTransactionButtonClicked)

        self._transactions_table = widgets.TransactionTableWidget()
        self._transactions_table.model().setInsertable(True)

        current_account = self._acc_selection_combo.currentAccount() 

        if current_account is not None:
            self.updateModel(current_account.id)
    
    def _initLayouts(self):
        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addWidget(self._insert_transaction_btn)
        buttons_layout.addWidget(self._remove_transaction_btn)
        buttons_layout.addWidget(self._cancel_transaction_btn)
        buttons_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self._acc_selection_combo, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        hbox.addLayout(buttons_layout)
        
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(hbox)
        main_layout.addWidget(self._transactions_table)
        self.setLayout(main_layout)
    
    def updateModel(self, account_id: int) -> int:
        self._transactions_table.model().selectAccount(account_id)
        self._transactions_table.resizeColumnsToContents()

    @QtCore.pyqtSlot(common.AccountBox.AccountData)
    def _onCurrentAccountChanged(self, account: common.AccountBox.AccountData):
        self.updateModel(account.id)

    @QtCore.pyqtSlot()
    def _onInsertTransactionButtonClicked(self):
        self._transactions_table.model().persistDraft()

    @QtCore.pyqtSlot()
    def _onCancelTransactionButtonClicked(self):
        self._transactions_table.model().discardDraft()

    @QtCore.pyqtSlot()
    def _onRemoveTransactionButtonClicked(self):
        current_item = self._transactions_table.currentItem()

        if current_item is None:
            return

        ret = QtWidgets.QMessageBox.question(
            self,
            'Delete Transaction',
            'You sure to delete the transaction?'
        )

        if ret == QtWidgets.QMessageBox.StandardButton.Yes:
            self._transactions_table.model().removeTransaction(current_item.id())