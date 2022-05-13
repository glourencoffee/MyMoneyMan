from __future__ import annotations
import decimal
import enum
import typing
from PyQt5        import QtCore
from PyQt5.QtCore import Qt
from mymoneyman   import models, utils

class AccountTreeProxyItem(models.GroupingProxyItem):
    """Represents an item in `AccountTreeProxyModel`.
    
    The class `AccountTreeProxyItem` extends `GroupingProxyItem` to allow account
    group items to be stored in the proxy model. Account group items are not part
    of a source model (`AccountTableModel`) and thus always returns `False` for
    `isSourceIndex()`.

    The method `account()` retrieves the account at `sourceIndex()` in the source
    model, or `None` if an item is an account group one.

    See Also
    --------
    `AccountTreeProxyModel`
    """

    __slots__ = ('_group', '_balance')

    def __init__(self, source_index_or_group: typing.Union[QtCore.QPersistentModelIndex, models.AccountGroup]):
        if isinstance(source_index_or_group, models.AccountGroup):
            source_index = QtCore.QPersistentModelIndex()
            self._group  = source_index_or_group
        else:
            source_index = source_index_or_group
            self._group  = None

        self._balance = None

        super().__init__(source_index)

    def isAccountGroup(self) -> bool:
        return self._group is not None

    def account(self) -> typing.Optional[models.Account]:
        """Returns the account's id if this item is an account, and `None` otherwise."""

        if self.isSourceIndex():
            source_index = self.sourceIndex()
            source_model: models.AccountTableModel = source_index.model()

            return source_model.account(source_index.row())

        return None
    
    def accountGroup(self) -> models.AccountGroup:
        account = self.account()

        if account is None:
            return self._group
        else:
            return account.type.group()

    def name(self, extended: bool = False, sep: str = ':') -> str:
        account = self.account()

        if account is not None:
            name = account.name
        elif self._group is not None:
            name = self._group.name
        else:
            name = ''

        parent = self.parent()

        if extended and parent and isinstance(parent, AccountTreeProxyItem):
            parent_name = parent.name(extended=True, sep=sep)
            
            if parent_name != '':
                name = parent_name + sep + name
        
        return name

    def balance(self) -> decimal.Decimal:
        if self._balance is None:
            account = self.account()

            if account is None:
                self._balance = decimal.Decimal(0)
            else:
                self._balance = account.balance()

                if self._balance != 0 and account.type.group() in (
                    models.AccountGroup.Liability, models.AccountGroup.Income, models.AccountGroup.Equity
                ):
                    self._balance *= -1
        
        return self._balance

    def cumulativeBalance(self, currency: typing.Optional[models.Currency] = None) -> decimal.Decimal:
        balance = self.balance()
        account = self.account()

        if balance != 0 and account is not None and currency is not None:
            quote = account.asset.quote(currency, two_way=True)

            if quote is not None:
                balance *= quote
        
        for child in self.children():
            balance += child.cumulativeBalance(currency or account.asset)

        return balance

    def childNames(self) -> typing.List[str]:
        return [child.name() for child in self.children() if isinstance(child, AccountTreeProxyItem)]

    def __repr__(self) -> str:
        parent = self.parent()

        if isinstance(parent, AccountTreeProxyItem):
            parent_name = "'" + parent.name() + "'"
        else:
            parent_name = None

        return (
            "AccountTreeProxyItem<"
                f"source_index={utils.indexLocation(self.sourceIndex())} "
                f"name='{self.name(extended=True)}' "
                f"parent={parent_name} "
                f"children={self.childNames()}"
            ">"
        )

class AccountTreeProxyModel(models.GroupingProxyModel):
    """Provides a hierarchical model of accounts.

    The class `AccountTreeProxyModel` extends `GroupingProxyModel` to group accounts
    in `AccountTableModel` by their parents, while respecting their hierarchy.

    An empty model provides indices of account groups:
    - Asset
    - Liability
    - Income
    - Expense
    - Equity
    
    A non-empty model places accounts into their appropriate groups:
    - Asset
        - Bank
            - Checking
            - Savings
        - Investments
    - Liability
        - Credit Card
        - Car Loan
    - Income
        - Salary
    - Expense
        - Grocery Store
    - Equity
        - USD

    In addition, the model allows [balance]

    See Also
    --------
    `AccountTableModel`
    """

    class Column(enum.IntEnum):
        """Enumerates the columns in this model class."""

        Name        = 0
        Description = 1
        Balance     = 2

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

        self._filter_groups         = list(models.AccountGroup)
        self._filter_groups_visible = False
    
    def setFilterGroup(self, group: models.AccountGroup, visible: bool = True):
        if set([group]) == set(self._filter_groups) and self._filter_groups_visible == visible:
            return
        
        self._filter_groups         = [group]
        self._filter_groups_visible = visible
        self.reset()

    def setFilterGroups(self, groups: typing.Iterable[models.AccountGroup]):
        if set(groups) == set(self._filter_groups):
            return

        self._filter_groups         = list(dict.fromkeys(groups))
        self._filter_groups_visible = True
        self.reset()

    def filterGroups(self) -> typing.List[models.AccountGroup]:
        return self._filter_groups.copy()
    
    def filterGroupsVisible(self) -> bool:
        return self._filter_groups_visible

    def itemFromAccountGroup(self, group: models.AccountGroup) -> typing.Optional[AccountTreeProxyItem]:
        for child in self._root_item.children():
            assert isinstance(child, AccountTreeProxyItem)

            if child.isAccountGroup() and child.accountGroup() == group:
                return child
            
        return None
    
    def itemFromAccount(self, account: models.Account) -> typing.Optional[AccountTreeProxyItem]:
        return self.invisibleRootItem().findChild(lambda item: item.account() is account)

    ################################################################################
    # Overriden methods (QAbstractItemModel)
    ################################################################################
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if orientation == Qt.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return AccountTreeProxyModel.Column(section).name

        return None

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(AccountTreeProxyModel.Column)

    ################################################################################
    # Overriden methods (QAbstractProxyModel)
    ################################################################################
    def setSourceModel(self, source_model: QtCore.QAbstractItemModel):
        if not isinstance(source_model, models.AccountTableModel):
            raise TypeError('source model is not an instance of AccountTableModel')

        super().setSourceModel(source_model)

    ################################################################################
    # Overriden methods (GroupingProxyModel)
    ################################################################################
    def resetRoot(self):
        super().resetRoot()
        
        if self._filter_groups_visible:
            for group in self._filter_groups:
                self.appendItem(AccountTreeProxyItem(group), self.invisibleRootItem())

    def filterAcceptsRow(self, source_row: int):
        account_table: models.AccountTableModel = self.sourceModel()
        account = account_table.account(source_row)

        return account.type.group() in self._filter_groups

    def createItemForRow(self, source_row: int) -> bool:
        account_table: models.AccountTableModel = self.sourceModel()
        account = account_table.account(source_row)

        # print('createItemForRow(): account', account.name)

        if account.parent_id is None:
            # print('createItemForRow(): placing account under root item')
            if self._filter_groups_visible:
                account_group = account.type.group()
                parent_item   = self.itemFromAccountGroup(account_group)

                if parent_item is None:
                    print('could not find group item for account group %s; falling back to using root item as parent', account_group)
                    parent_item = self._root_item
            else:
                parent_item = self._root_item    
        else:
            parent_item = self.itemFromAccount(account.parent)

            # print('createItemForRow(): parent account not found:', account.parent)

            if parent_item is None:
                return False

        self.createItem(source_row, parent_item)
        return True

    def createItemForIndex(self, source_index: QtCore.QPersistentModelIndex) -> models.GroupingProxyItem:
        return AccountTreeProxyItem(source_index)

    def dataForItem(self, item: models.GroupingProxyItem, column: int, role: int = Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None

        assert isinstance(item, AccountTreeProxyItem)

        Column = AccountTreeProxyModel.Column
        column = Column(column)

        if item.isAccountGroup():
            if column == Column.Name:
                return item.accountGroup().name
        else:
            account: typing.Optional[models.Account] = item.account()

            if account is None:
                return None

            if   column == Column.Name:        return account.name
            elif column == Column.Description: return account.description
            elif column == Column.Balance:     return account.asset.formatWithCode(item.cumulativeBalance(), account.precision)

        return None