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
        self._acc_selection_combo.currentIndexChanged.connect(self._onCurrentIndexChanged)

        self._split_transaction_btn   = QtWidgets.QPushButton(QtGui.QIcon(), 'Split')
        self._persist_transaction_btn = QtWidgets.QPushButton(QtGui.QIcon(':/icons/insert.png'), 'Save')
        self._discard_transaction_btn = QtWidgets.QPushButton(QtGui.QIcon(':/icons/cancel.png'), 'Cancel')
        self._remove_transaction_btn  = QtWidgets.QPushButton(QtGui.QIcon(':/icons/delete.png'), 'Remove')

        self._persist_transaction_btn.setEnabled(False)
        self._discard_transaction_btn.setEnabled(False)

        self._split_transaction_btn.clicked.connect(self._onSplitTransactionButtonClicked)
        self._persist_transaction_btn.clicked.connect(self._onPersistTransactionButtonClicked)
        self._discard_transaction_btn.clicked.connect(self._onDiscardTransactionButtonClicked)
        self._remove_transaction_btn.clicked.connect(self._onRemoveTransactionButtonClicked)

        self._transactions_table = widgets.TransactionTableWidget()
        self._transactions_table.model().setInsertable(True)
        self._transactions_table.model().draftStateChanged.connect(self._onDraftStateChanged)

        account    = self._acc_selection_combo.currentAccount() 
        account_id = account.id if account is not None else None
        
        self.selectAccount(account_id)
    
    def _initLayouts(self):
        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addWidget(self._split_transaction_btn)
        buttons_layout.addWidget(self._persist_transaction_btn)
        buttons_layout.addWidget(self._discard_transaction_btn)
        buttons_layout.addWidget(self._remove_transaction_btn)
        buttons_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self._acc_selection_combo, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        hbox.addLayout(buttons_layout)
        
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(hbox)
        main_layout.addWidget(self._transactions_table)
        self.setLayout(main_layout)
    
    def refresh(self):
        current_account = self._acc_selection_combo.currentAccount()

        self._acc_selection_combo.populate()

        if current_account is not None:
            self._acc_selection_combo.setCurrentAccount(current_account.id)

    def selectAccount(self, account_id: typing.Optional[int]):
        if account_id is None:
            self._acc_selection_combo.setCurrentIndex(-1)
            self._transactions_table.model().reset()
        else:
            self._acc_selection_combo.setCurrentAccount(account_id)
            self._transactions_table.model().selectAccount(account_id)
            self._transactions_table.resizeColumnsToContents()

    @QtCore.pyqtSlot(int)
    def _onCurrentIndexChanged(self, index: int):
        account    = self._acc_selection_combo.currentAccount()
        account_id = account.id if account is not None else None
        
        self.selectAccount(account_id)

    @QtCore.pyqtSlot(bool)
    def _onDraftStateChanged(self, has_draft: bool):
        self._persist_transaction_btn.setEnabled(has_draft)
        self._discard_transaction_btn.setEnabled(has_draft)

    @QtCore.pyqtSlot()
    def _onSplitTransactionButtonClicked(self):
        transaction_index = self._transactions_table.currentIndex()
        transaction_item  = self._transactions_table.model().itemFromIndex(transaction_index)

        if transaction_item is None:
            return

        dialog = widgets.SplitTransactionDialog(transaction_item.id())
        
        if dialog.exec():
            self._transactions_table.model().refresh(transaction_index)

    @QtCore.pyqtSlot()
    def _onPersistTransactionButtonClicked(self):
        self._transactions_table.model().persistDraft()

    @QtCore.pyqtSlot()
    def _onDiscardTransactionButtonClicked(self):
        self._transactions_table.model().discardDraft()

    @QtCore.pyqtSlot()
    def _onRemoveTransactionButtonClicked(self):
        if self._transactions_table.currentRow() == self._transactions_table.model().insertableRow():
            return

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