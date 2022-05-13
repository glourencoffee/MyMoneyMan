import typing
from PyQt5        import QtCore
from PyQt5.QtCore import Qt
from mymoneyman   import models

class AccountNameProxyModel(QtCore.QSortFilterProxyModel):
    """Provides a list model of extended account names.

    The class `AccountNameProxyModel` extends `QSortFilterProxyModel` to filter
    accounts in `AccountTableModel` so that only extended account names are shown.
    For example, say the database stores the following account hierarchy:
    - Asset
        - Bank
            - Checking
            - Savings
        - Investments
    - Liability
        - Credit Card
    - Income
        - Salary
    - Expense
        - Grocery Store

    This class will provide the following list of account names:
    - Asset:Bank
    - Asset:Bank:Checking
    - Asset:Bank:Savings
    - Asset:Investments
    - Liability:Credit Card
    - Income:Salary
    - Expense:Grocery Store

    Note that account groups are never shown as items.
    
    By default, this class uses colon (:) as separator and shows accounts of all
    groups except `AccountGroup.Equity`. This may be changed by calling the methods
    `setSeparator()` and `setGroups()`, or by passing the desired values upon
    construction of this class.

    See Also
    --------
    `AccountTableModel`
    """

    def __init__(self,
                 sep: str = ':',
                 groups: typing.Iterable[models.AccountGroup] = models.AccountGroup.allButEquity(),
                 parent: typing.Optional[QtCore.QObject] = None
    ):
        super().__init__(parent=parent)

        self._sep    = sep
        self._groups = set(groups)

    def setSeparator(self, sep: str):
        """Sets `sep` as account name separator.
        
        Calling this method has no effect if `sep` is same as `separator()`.
        """

        if sep != self._sep:
            self._sep = sep
            self.invalidateFilter()
    
    def separator(self) -> str:
        """Returns the account name separator used by this model."""

        return self._sep

    def setGroups(self, groups: typing.Iterable[models.AccountGroup]):
        """Sets which account groups are accepted.
        
        Calling this method causes this model to be populated only
        with accounts whose group are in `groups`. All other accounts
        are filtered out.

        Does nothing if `set(groups)` is same as `self.groups()`.
        """

        groups = set(groups)

        if groups != self._groups:
            self._groups = groups
            self.invalidate()

    def groups(self) -> typing.Set[models.AccountGroup]:
        """Returns the account group filter used by this model."""

        return self._groups.copy()

    def account(self, proxy_row: int) -> models.Account:
        """Returns the account at a row of this model."""

        proxy_index  = self.index(proxy_row, 0)
        source_index = self.mapToSource(proxy_index)
        source_model: models.AccountTableModel = self.sourceModel()

        return source_model.account(source_index.row())

    def rowOf(self, account: models.Account) -> int:
        """Returns which row of this model an account is at.
        
        If the name of `account` is currently being provided by this model,
        returns the row which `account` is at. Otherwise, returns -1.
        """

        source_model: models.AccountTableModel = self.sourceModel()
        source_row = source_model.rowOf(account)

        if source_row == -1:
            return -1
        
        source_column = source_model.columnIndex(models.Account.name)
        source_index  = source_model.index(source_row, source_column)
        proxy_index   = self.mapFromSource(source_index)

        return proxy_index.row()

    ################################################################################
    # Overriden methods
    ################################################################################
    def setSourceModel(self, model: QtCore.QAbstractItemModel):
        """Reimplements `QAbstractProxyModel.setSourceModel()`."""

        if not isinstance(model, models.AccountTableModel):
            raise TypeError('model is not an instance of AccountTableModel')
        
        super().setSourceModel(model)

        self.setSortRole(Qt.ItemDataRole.DisplayRole)
        self.setFilterKeyColumn(0)
        self.sort(0)

    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:
        """Reimplements `QSortFilterProxyModel.filterAcceptsRow()`."""

        account: models.Account = self.sourceModel().account(source_row)
        
        return account.group() in self._groups

    def filterAcceptsColumn(self, source_column: int, source_parent: QtCore.QModelIndex) -> bool:
        """Reimplements `QSortFilterProxyModel.filterAcceptsColumn()`."""

        account_table: models.AccountTableModel = self.sourceModel()
        
        return source_column == account_table.columnIndex(models.Account.name)

    def lessThan(self, left: QtCore.QModelIndex, right: QtCore.QModelIndex) -> bool:
        """Reimplements `QSortFilterProxyModel.lessThan()`."""

        left_account  = self.sourceModel().account(left.row())
        right_account = self.sourceModel().account(right.row())

        return left_account.extendedName(sep=self._sep) < right_account.extendedName(sep=self._sep)
    
    def data(self, proxy_index: QtCore.QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> typing.Any:
        """Reimplements `QAbstractItemModel.data()`."""

        if role != Qt.ItemDataRole.DisplayRole:
            return super().data(proxy_index, role)

        return self.account(proxy_index.row()).extendedName(sep=self._sep)