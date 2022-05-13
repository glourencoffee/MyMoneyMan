import typing
from PyQt5      import QtCore, QtGui, QtWidgets
from mymoneyman import models, widgets

class TransactionPage(QtWidgets.QWidget):
    transactionChanged = QtCore.pyqtSignal(models.Transaction)

    def __init__(self, account_model: models.AccountTableModel, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

        self._transaction_table_model = models.TransactionTableModel()
        self._account_table_model     = account_model

        self._initWidgets()
        self._initLayouts()
    
    def _initWidgets(self):
        self._acc_selection_combo = widgets.AccountCombo()
        self._acc_selection_combo.setEditable(True)
        self._acc_selection_combo.model().setSourceModel(self._account_table_model)
        self._acc_selection_combo.currentAccountChanged.connect(self._onCurrentAccountChanged)

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

        self._transactions_table = widgets.TransactionTableWidget(self._account_table_model)
        self._transactions_table.model().setSourceModel(self._transaction_table_model)
        self._transactions_table.transactionChanged.connect(self._onTransactionChanged)
        self._transactions_table.currentRowChanged.connect(self._onTableCurrentRowChanged)
    
    def _initLayouts(self):
        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addWidget(self._split_transaction_btn)
        buttons_layout.addWidget(self._persist_transaction_btn)
        buttons_layout.addWidget(self._discard_transaction_btn)
        buttons_layout.addWidget(self._remove_transaction_btn)
        buttons_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self._acc_selection_combo, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        hbox.addLayout(buttons_layout)
        
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(hbox)
        main_layout.addWidget(self._transactions_table)
        self.setLayout(main_layout)

    def setSession(self, session):
        self._transaction_table_model.select(session)

    def refresh(self):
        current_account = self._acc_selection_combo.currentAccount()

        if current_account is not None:
            self._acc_selection_combo.setCurrentAccount(current_account.id)

    def setCurrentAccount(self, account: typing.Optional[models.Account]):
        self._acc_selection_combo.setCurrentAccount(account)

        if account is None:
            self._transactions_table.model().setAccount(None)

    def _toggleButtonsState(self, transaction: models.Transaction):
        changed = transaction.hasChanged() or any(sub.hasChanged() for sub in transaction.subtransactions)

        self._persist_transaction_btn.setEnabled(changed)
        self._discard_transaction_btn.setEnabled(changed)

    @QtCore.pyqtSlot(models.Account)
    def _onCurrentAccountChanged(self, account: models.Account):
        self._transactions_table.model().setAccount(account)
        self._transactions_table.model().setInsertable(True)

    @QtCore.pyqtSlot(bool)
    def _onDraftStateChanged(self, has_draft: bool):
        self._persist_transaction_btn.setEnabled(has_draft)
        self._discard_transaction_btn.setEnabled(has_draft)

    @QtCore.pyqtSlot()
    def _onSplitTransactionButtonClicked(self):
        current_row = self._transactions_table.currentRow()

        if current_row == -1:
            return

        transaction = self._transactions_table.model().transaction(current_row)

        dialog = widgets.SubtransactionEditDialog(self._account_table_model, transaction)
        
        if dialog.exec():
            self._transactions_table.model().persist(current_row)
        else:
            self._transactions_table.model().discard(current_row)

    @QtCore.pyqtSlot(int, models.Transaction)
    def _onTransactionChanged(self, row: int, transaction: models.Transaction):
        self._toggleButtonsState(transaction)
        self.transactionChanged.emit(transaction)

    @QtCore.pyqtSlot(int, int)
    def _onTableCurrentRowChanged(self, current: int, previous: int):
        transaction = self._transactions_table.model().transaction(current)

        self._toggleButtonsState(transaction)

    @QtCore.pyqtSlot()
    def _onPersistTransactionButtonClicked(self):
        current_row = self._transactions_table.currentRow()

        self._transactions_table.model().persist(current_row)

    @QtCore.pyqtSlot()
    def _onDiscardTransactionButtonClicked(self):
        self._transactions_table.model().discard(self._transactions_table.currentRow())

    @QtCore.pyqtSlot()
    def _onRemoveTransactionButtonClicked(self):
        transaction = self._transactions_table.currentTransaction()

        if transaction is None:
            return

        ret = QtWidgets.QMessageBox.question(
            self,
            'Delete Transaction',
            'Are you sure to delete this transaction?'
        )

        if ret == QtWidgets.QMessageBox.StandardButton.Yes:
            self._transaction_table_model.delete(transaction)