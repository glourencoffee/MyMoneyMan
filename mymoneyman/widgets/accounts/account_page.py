import functools
import typing
from PyQt5              import QtCore, QtGui, QtWidgets
from mymoneyman.widgets import accounts as widgets
from mymoneyman         import models

class AccountPage(QtWidgets.QWidget):
    accountCreated = QtCore.pyqtSignal(int)
    accountDeleted = QtCore.pyqtSignal(int)
    accountEdited  = QtCore.pyqtSignal(int)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        models.sql.set_engine('m3db.sqlite3')

        self._initWidgets()
        self._initLayouts()
    
    def _initWidgets(self):
        self._initToolBar()
        self._balance_box = widgets.BalanceBox()
        self._balance_box.expandAll()
        self._balance_box.currentChanged.connect(self._onCurrentTreeItemChanged)

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
        main_layout.addWidget(self._balance_box)
        main_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        self.setLayout(main_layout)

    @QtCore.pyqtSlot()
    def _onListLayoutAction(self):
        self._balance_box.setListLayout()

    @QtCore.pyqtSlot()
    def _onGridLayoutAction(self):
        self._balance_box.setGridLayout()

    @QtCore.pyqtSlot()
    def _onAddAccountAction(self):
        # TODO: tr()
        dialog = widgets.AccountEditDialog(widgets.AccountEditDialog.EditionMode.Creation, self)

        if dialog.exec():
            account_type  = dialog.accountType()
            account_group = models.AccountGroup.fromAccountType(account_type)

            self._balance_box.updateBalances(account_group)
            self._balance_box.expandAll()
            
            self.accountCreated.emit(dialog.accountId())

    @QtCore.pyqtSlot()
    def _onDelAccountAction(self):
        selected_item = self._balance_box.selectedItem()

        if selected_item is None:
            return

        ret = QtWidgets.QMessageBox.question(self, 'Delete account', f"Are you sure to delete account '{selected_item.name()}'?")

        if ret != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        if models.AccountTreeModel().removeAccount(selected_item.id()):
            account_group = self._balance_box.selectedGroup()

            self._balance_box.updateBalances(account_group)
            self._balance_box.expandAll()
            
            self.accountDeleted.emit(selected_item.id())
    
    @QtCore.pyqtSlot()
    def _onEditAccountAction(self):
        selected_item = self._balance_box.selectedItem()

        if selected_item is None:
            return

        dialog = widgets.AccountEditDialog(widgets.AccountEditDialog.EditionMode.Edition, self)
        dialog.setName(selected_item.name())
        dialog.setDescription(selected_item.description())
        
        if dialog.exec():
            account_type  = dialog.accountType()
            account_group = models.AccountGroup.fromAccountType(account_type)

            self._balance_box.updateBalances(account_group)
            self._balance_box.expandAll()

            self.accountEdited.emit(selected_item.id())
    
    @QtCore.pyqtSlot(widgets.AccountTreeWidget, models.AccountTreeItem)
    def _onCurrentTreeItemChanged(self, tree: widgets.AccountTreeWidget, item: models.AccountTreeItem):
        self._del_account_action.setEnabled(True)
        self._edit_account_action.setEnabled(True)