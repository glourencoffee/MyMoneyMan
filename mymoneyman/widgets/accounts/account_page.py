import functools
import sqlalchemy as sa
import sqlalchemy.orm
import typing
from PyQt5      import QtCore, QtGui, QtWidgets
from mymoneyman import widgets, models

class AccountPage(QtWidgets.QWidget):
    accountCreated       = QtCore.pyqtSignal(models.Account)
    accountDeleted       = QtCore.pyqtSignal(models.Account)
    accountEdited        = QtCore.pyqtSignal(models.Account)
    accountClicked       = QtCore.pyqtSignal(models.Account)
    accountDoubleClicked = QtCore.pyqtSignal(models.Account)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

        self._account_table_model = models.AccountTableModel()

        self._initWidgets()
        self._initLayouts()
    
    def _initWidgets(self):
        self._initToolBar()
        self._account_tree_box = widgets.AccountTreeBox()
        self._account_tree_box.setModel(self._account_table_model)
        self._account_tree_box.expandAll()
        self._account_tree_box.currentChanged.connect(self._onAccountTreeBoxCurrentChanged)
        self._account_tree_box.doubleClicked.connect(self._onAccountTreeBoxDoubleClicked)

    def _initToolBar(self):
        self._tool_bar = QtWidgets.QToolBar()
        self._tool_bar.setIconSize(QtCore.QSize(32, 32))

        # TODO: tr()
        self._add_account_action  = self._tool_bar.addAction(QtGui.QIcon(':/icons/add-account.png'),  'Create account', self._onAddAccountAction)
        self._del_account_action  = self._tool_bar.addAction(QtGui.QIcon(':/icons/del-account.png'),  'Delete account', self._onDelAccountAction)
        self._edit_account_action = self._tool_bar.addAction(QtGui.QIcon(':/icons/edit-account.png'), 'Edit account',   self._onEditAccountAction)
        self._del_account_action.setEnabled(False)
        self._edit_account_action.setEnabled(False)
        
        self._tool_bar.addSeparator()

        self._list_layout_action = self._tool_bar.addAction(QtGui.QIcon(':/icons/list-layout.png'), 'Show as list', self._onListLayoutAction)
        self._grid_layout_action = self._tool_bar.addAction(QtGui.QIcon(':/icons/grid-layout.png'), 'Show as grid', self._onGridLayoutAction)

    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._tool_bar)
        main_layout.addWidget(self._account_tree_box)
        main_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        self.setLayout(main_layout)

    def setSession(self, session: sa.orm.Session):
        self._account_table_model.select(session)

    def refresh(self):
        self._account_tree_box.refreshBalances()

    @QtCore.pyqtSlot()
    def _onListLayoutAction(self):
        self._account_tree_box.setListLayout()

    @QtCore.pyqtSlot()
    def _onGridLayoutAction(self):
        self._account_tree_box.setGridLayout()

    @QtCore.pyqtSlot()
    def _onAddAccountAction(self):
        # TODO: tr()
        dialog = widgets.AccountEditDialog(self._account_table_model, self)

        if dialog.exec():
            self.accountCreated.emit(dialog.account())

    @QtCore.pyqtSlot()
    def _onDelAccountAction(self):
        account = self._account_tree_box.currentAccount()

        if account is None:
            return

        ret = QtWidgets.QMessageBox.question(
            self,
            'Delete account',
            f"Are you sure to delete account '{account.extendedName()}'?"
        )

        if ret == QtWidgets.QMessageBox.StandardButton.Yes:
            self._account_table_model.delete(account)
            self.accountDeleted.emit(account)
    
    @QtCore.pyqtSlot()
    def _onEditAccountAction(self):
        account = self._account_tree_box.currentAccount()

        if account is None:
            return

        dialog = widgets.AccountEditDialog(self._account_table_model, self)
        dialog.setAccount(account)

        if dialog.exec():
            self.accountEdited.emit(account)
    
    @QtCore.pyqtSlot(models.Account)
    def _onAccountTreeBoxCurrentChanged(self, account: models.Account):
        self._del_account_action.setEnabled(True)
        self._edit_account_action.setEnabled(True)
    
    @QtCore.pyqtSlot(models.Account)
    def _onAccountTreeBoxClicked(self, account: models.Account):
        self.accountClicked.emit(account)

    @QtCore.pyqtSlot(models.Account)
    def _onAccountTreeBoxDoubleClicked(self, account: models.Account):
        self.accountDoubleClicked.emit(account)