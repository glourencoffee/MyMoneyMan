from __future__ import annotations
import collections
import decimal
import enum
import typing
import sqlalchemy as sa
import sqlalchemy_utils as sa_utils
from PyQt5      import QtCore
from mymoneyman import models

class AccountType(enum.IntEnum):
    Asset      = enum.auto()
    Cash       = enum.auto()
    Bank       = enum.auto()
    Receivable = enum.auto()
    Security   = enum.auto()
    Liability  = enum.auto()
    CreditCard = enum.auto()
    Payable    = enum.auto()
    Income     = enum.auto()
    Expense    = enum.auto()
    Equity     = enum.auto()

class AccountGroup(enum.IntEnum):
    Asset     = 0
    Liability = 1
    Income    = 2
    Expense   = 3
    Equity    = 4

    @staticmethod
    def allButEquity() -> typing.Tuple[AccountGroup]:
        return (AccountGroup.Asset, AccountGroup.Liability, AccountGroup.Income, AccountGroup.Expense)

    @staticmethod
    def fromAccountType(account_type: AccountType) -> AccountGroup:
        T = AccountType

        if account_type in (T.Asset, T.Cash, T.Bank, T.Receivable, T.Security):
            return AccountGroup.Asset
        elif account_type in (T.Liability, T.CreditCard, T.Payable):
            return AccountGroup.Liability
        elif account_type == T.Income:
            return AccountGroup.Income
        elif account_type == T.Expense:
            return AccountGroup.Expense
        else:
            return AccountGroup.Equity

    def accountTypes(self) -> typing.Tuple[AccountType]:
        T = AccountType

        if self == AccountGroup.Asset:
            return (T.Asset, T.Cash, T.Bank, T.Receivable, T.Security)
        elif self == AccountGroup.Liability:
            return (T.Liability, T.CreditCard, T.Payable)
        elif self == AccountGroup.Income:
            return (T.Income,)
        elif self == AccountGroup.Expense:
            return (T.Expense,)
        else:
            return (T.Equity,)

class Account(models.sql.Base):
    """Defines the SQL table `account`."""

    __tablename__ = 'account'

    id          = sa.Column(sa.Integer,           primary_key=True, autoincrement=True)
    type        = sa.Column(sa.Enum(AccountType), nullable=False)
    name        = sa.Column(sa.String,            nullable=False)
    description = sa.Column(sa.String)
    parent_id   = sa.Column(sa.ForeignKey('account.id'))
    currency_id = sa.Column(sa.ForeignKey('currency.id'))
    security_id = sa.Column(sa.ForeignKey('security.id'))

    def __repr__(self) -> str:
        return f"Account<id={self.id} name='{self.name}' type={self.type} parent_id={self.parent_id} asset_id={self.asset_id}>"

def _makeExtendedAccountViewStatement():
    # WITH RECURSIVE cte(id, type, description, parent_id, name) AS
    # (
    #   SELECT id, type, description, parent_id, name
    #     FROM account
    #    WHERE parent_is IS NULL
    #    UNION
    #   SELECT c.id, c.type, c.description, c.parent_id, p.name || ':' || c.name
    #     FROM cte     AS p
    #     JOIN account AS c ON c.parent_id = p.id
    # )
    # SELECT * FROM cte

    A = Account

    top_stmt = (
        sa.select(
            A.id,
            A.type,
            A.description,
            A.parent_id,
            A.name
        )
        .where(A.parent_id == None)
        .cte('cte', recursive=True)
    )

    Parent = sa.orm.aliased(top_stmt, name='p')
    Child  = sa.orm.aliased(A,        name='c')

    cte = top_stmt.union(
        sa.select(
            Child.id,
            Child.type,
            Child.description,
            Child.parent_id,
            (Parent.c.name + sa.literal(':') + Child.name).label('name')
        )
        .select_from(Parent)
        .join(Child, Parent.c.id == Child.parent_id)
    )

    stmt = cte.select()

    return stmt

from sqlalchemy_utils.view import CreateView
from sqlalchemy.ext import compiler

# https://github.com/kvesteri/sqlalchemy-utils/issues/396
@sa.ext.compiler.compiles(sa_utils.view.CreateView)
def compile_create_materialized_view(element, compiler, **kw):
    return 'CREATE {}VIEW IF NOT EXISTS {} AS {}'.format(
        'MATERIALIZED ' if element.materialized else '',
        element.name,
        compiler.sql_compiler.process(element.selectable, literal_binds=True),
)

class ExtendedAccountView(models.sql.Base):
    """Provides a view that extends account names based on account hierarchy.

    The purpose of this class is to combine names of parented accounts into a single name
    separated by colon (:). It does so by using a view that selects all information from
    the table `account` with a recursive CTE. This allows a responsive lookup of account
    names even if the name of any account in an account hierarchy is changed.

    Here's an example to illustrate what this class does in pratice. Say four accounts
    are stored in the database table `account`, whose name and parent are shown as follows:

    | Name           | Parent         |
    |----------------|----------------|
    | Current Assets | NULL           |
    | Wallet         | Current Assets |
    | Banks          | Current Assets |
    | Savings        | Banks          |
    
    Querying all account names on this view will thus return the following results:
    - 'Current Assets'
    - 'Current Assets:Wallet'
    - 'Current Assets:Banks'
    - 'Current Assets:Banks:Savings'

    Columns in this class are an exact match to columns in the ORM class `Account`, with
    the only difference being the content of the column `name`.
    """

    __table__ = sa_utils.create_view('extended_account_view', _makeExtendedAccountViewStatement(), models.sql.meta)

    id          = __table__.c.id
    type        = __table__.c.type
    name        = __table__.c.name
    description = __table__.c.description
    parent_id   = __table__.c.parent_id

def _makeAccountAssetViewStatement():
    # SELECT a.id        AS account_id,
    #        c.id        AS asset_id,
    #        TRUE        AS asset_is_currency,
    #        NULL        AS asset_scope,
    #        c.code      AS asset_code,
    #        c.symbol    AS asset_symbol,
    #        c.name      AS asset_name,
    #        c.code      AS currency_code,
    #        c.precision AS currency_precision,
    #        c.is_fiat   AS currency_is_fiat
    #   FROM account  AS a
    #   JOIN currency AS c ON a.currency_id = c.id
    #  UNION
    # SELECT a.id        AS account_id,
    #        s.id        AS asset_id,
    #        FALSE       AS asset_is_currency,
    #        s.mic       AS asset_scope,
    #        s.code      AS asset_code,
    #        NULL        AS asset_symbol,
    #        s.name      AS asset_name,
    #        c.code      AS currency_code,
    #        c.precision AS currency_precision,
    #        c.is_fiat   AS currency_is_fiat
    #   FROM account  AS a
    #   JOIN security AS s ON a.security_id = s.id
    #   JOIN currency AS c ON s.currency_id = c.id

    A = sa.orm.aliased(Account,         name='a')
    C = sa.orm.aliased(models.Currency, name='c')
    S = sa.orm.aliased(models.Security, name='s')

    s1 = (
        sa.select(
            A.id.label('account_id'),
            C.id.label('asset_id'),
            sa.literal(True).label('asset_is_currency'),
            sa.literal(None).label('asset_scope'),
            C.code.label('asset_code'),
            C.symbol.label('asset_symbol'),
            C.name.label('asset_name'),
            C.code.label('currency_code'),
            C.precision.label('currency_precision'),
            C.is_fiat.label('currency_is_fiat')
          )
          .select_from(A)
          .join(C, A.currency_id == C.id)
    )
    
    s2 = (
        sa.select(
            A.id.label('account_id'),
            S.id.label('asset_id'),
            sa.literal(False).label('asset_is_currency'),
            S.mic.label('asset_scope'),
            S.code.label('asset_code'),
            sa.literal(None).label('asset_symbol'),
            S.name.label('asset_name'),
            C.code.label('currency_code'),
            C.precision.label('currency_precision'),
            C.is_fiat.label('currency_is_fiat')
          )
          .select_from(A)
          .join(S, A.security_id == S.id)
          .join(C, S.currency_id == C.id)
    )

    return s1.union(s2)

class AccountAssetView(models.sql.Base):
    __table__ = sa_utils.create_view('account_asset_view', _makeAccountAssetViewStatement(), models.sql.meta)

    account_id         = __table__.c.account_id
    asset_id           = __table__.c.asset_id
    asset_is_currency  = __table__.c.asset_is_currency
    asset_scope        = __table__.c.asset_scope
    asset_code         = __table__.c.asset_code
    asset_symbol       = __table__.c.asset_symbol
    asset_name         = __table__.c.asset_name
    currency_code      = __table__.c.currency_code
    currency_precision = __table__.c.currency_precision
    currency_is_fiat   = __table__.c.currency_is_fiat

AccountInfo = collections.namedtuple('AccountInfo', ['id', 'name', 'type'])

class AccountTreeItem:
    """Contains information of an item of `AccountTreeModel`."""

    __slots__ = (
        '_id',
        '_type',
        '_name',
        '_desc',
        '_parent',
        '_children'
    )

    def __init__(self, 
                 id: typing.Optional[int],
                 type: AccountType,
                 name: str,
                 description: str,
                 parent: typing.Optional[AccountTreeItem]
    ):
        self._id              = id
        self._type            = type
        self._name            = name
        self._desc            = description
        self._parent          = parent
        self._children        = []

    def id(self) -> typing.Optional[int]:
        return self._id

    def type(self) -> AccountGroupType:
        return self._type

    def name(self) -> str:
        return self._name

    def extendedName(self, sep: str = ':') -> str:
        name = self._name

        if self._parent is not None:
            return self._parent.extendedName() + sep + name

        return name

    def description(self) -> str:
        return self._desc

    def parent(self) -> typing.Optional[AccountTreeItem]:
        return self._parent

    def children(self) -> typing.List[AccountTreeItem]:
        return self._children.copy()

    def nestedChildren(self) -> typing.List[AccountTreeItem]:
        children = []

        for child in self._children:
            children.append(child)
            children += child.nestedChildren()
        
        return children

    def appendChild(self, child: AccountTreeItem):
        self._children.append(child)

    def findChild(self, id: int) -> typing.Optional[AccountTreeItem]:
        for child in self._children:
            if child.id == id:
                return child
            
            return child.findChild(id)
        
        return None

    def child(self, row: int) -> typing.Optional[AccountTreeItem]:
        try:
            return self._children[row]
        except IndexError:
            return None
    
    def childCount(self) -> int:
        return len(self._children)

    def row(self) -> int:
        if self._parent is None:
            return 0
        
        return self._parent._children.index(self)

    def __repr__(self) -> str:
        if self._parent is None:
            parent_name = None
        else:
            parent_name = f"'{self._parent._name}'"

        children_names = tuple(child._name for child in self._children)

        return f"AccountTreeItem<type={self._type} name='{self._name}' id={self._id} parent={parent_name} children={children_names}>"

class AccountTreeModel(QtCore.QAbstractItemModel):
    """
    Provides a tree model for account groups that is composed of static top-level
    items and dynamic items stored in the database.
    
    There are exactly four static top-level items, one for each account group type,
    namely: assets, liabilities, income, and expenses. Top-level items are fixed
    and cannot be removed. That means if this model is assigned to a `QTreeView`,
    for example, these items will always be present. To access a top-level item,
    call `topLevelItem()` by passing a group type as parameter.

    All other tree items, so-called *dynamic items*, are populated by querying the
    database with `select()`. Dynamic items, as well as top-level items, can be
    retrieved by calling `itemFromIndex().`

    This class can also be used to insert and remove groups to/from the database
    with the methods `addGroup()` and `removeGroup()`, respectively. To check whether
    a group exists, call `hasGroup()`.
    """

    __slots__ = '_top_level_items'

    def __init__(self, parent: typing.Optional[QObject] = None):
        super().__init__(parent)

        self._resetTopLevelItems([])

    def reset(self):
        self.layoutAboutToBeChanged()
        self._resetTopLevelItems([])
        self.layoutChanged()

    def select(self, groups: typing.Sequence[AccountGroup]):
        """Retrieves all accounts groups from the database into this model."""

        account_groups = tuple(groups)
        account_types  = set()

        for group in account_groups:
            for at in group.accountTypes():
                account_types.add(at)

        account_info = collections.defaultdict(list)

        with models.sql.get_session() as session:
            #   SELECT * 
            #     FROM account
            #    WHERE type in :account_types
            # ORDER BY type, parent_id, id
            stmt = (
                sa.select(Account)
                  .where(Account.type.in_(tuple(account_types)))
                  .order_by(Account.type, Account.parent_id, Account.id)
            )

            result = session.execute(stmt).all()

            for t in result:
                acc: Account = t[0]
                account_info[acc.parent_id].append((acc.id, acc.type, acc.name))

        self.layoutAboutToBeChanged.emit()
        self._resetTopLevelItems(account_groups)

        try:
            def read_recursive(item: AccountTreeItem):
                try:
                    info_list = account_info[item.id()]
                except KeyError:
                    return

                for acc_id, acc_type, acc_name in info_list:
                    child = AccountTreeItem(acc_id, acc_type, acc_name, '', item)
                    read_recursive(child)
                    
                    item.appendChild(child)

            top_level_list = account_info.pop(None)

            for acc_id, acc_type, acc_name in top_level_list:
                acc_group = AccountGroup.fromAccountType(acc_type)

                top_level_item = self.topLevelItem(acc_group)

                child = AccountTreeItem(acc_id, acc_type, acc_name, '', top_level_item)
                read_recursive(child)

                top_level_item.appendChild(child)

        except KeyError:
            pass

        self.layoutChanged.emit()

    def hasAccount(self, name: str, type: AccountType, parent_id: typing.Optional[int]) -> bool:
        """Returns whether a group with the given values exists in the database."""

        # TODO: `type` only has relevance when parent_id is None.

        with models.sql.get_session() as session:
            # SELECT EXISTS(
            #   SELECT id
            #     FROM account
            #    WHERE name      = :name
            #      AND type      = :type
            #      AND parent_id = :parent_id
            # )

            result = session.execute(
                sa.exists(Account.id)
                    .where(
                        sa.and_(
                            Account.name      == name,
                            Account.type      == type,
                            Account.parent_id == parent_id
                        )
                    )
                    .select()
            ).first()

            return result[0]

    def addAccount(self, name: str, type: AccountType, description: str, parent_id: typing.Optional[int], asset_id: int) -> int:
        """TODO"""

        if self.hasAccount(name, type, parent_id):
            return -1

        with models.sql.get_session() as session:
            acc = Account(
                name            = name,
                type            = type,
                description     = description,
                parent_id       = parent_id
            )

            if type == AccountType.Security:
                acc.security_id = asset_id
            else:
                acc.currency_id = asset_id

            session.add(acc)
            session.commit()

            self.layoutAboutToBeChanged.emit()

            top_level_item = self.topLevelItem(AccountGroup.fromAccountType(type))

            if parent_id is None:
                child = AccountTreeItem(acc.id, type, name, description, top_level_item)
                top_level_item.appendChild(child)
            else:
                parent_item = top_level_item.findChild(acc.id)

                if parent_item is not None:
                    child = AccountTreeItem(acc.id, type, name, description, parent_item)
                    parent_item.appendChild(child)

            self.layoutChanged.emit()

            return acc.id

    def removeAccount(self, id: int) -> bool:
        """Removes an account from the database given its id."""

        with models.sql.get_session() as session:
            account = session.query(Account).filter(Account.id == id).first()

            if account is None:
                return False

            session.delete(account)
            session.commit()
        
        index = self.indexFromId(id)

        if index.isValid():
            self.layoutAboutToBeChanged.emit()
            self.removeRow(0, index.parent())
            self.layoutChanged.emit()

        return True

    def topLevelItem(self, group: AccountGroup) -> typing.Optional[AccountTreeItem]:
        """Returns a top-level item by group type."""

        return self._top_level_items[group.value]

    def indexFromId(self, account_id: int) -> QtCore.QModelIndex:
        for row in range(self.rowCount()):
            top_level_index = self.index(row, 0)

            index = self._indexFromId(account_id, top_level_index)

            if index.isValid():
                return index

        return QtCore.QModelIndex()

    def itemFromIndex(self, index: QtCore.QModelIndex) -> typing.Optional[AccountTreeItem]:
        """Returns an item by its associated index if `index` is valid, and `None` otherwise."""

        if not index.isValid():
            return None

        return index.internalPointer()

    ################################################################################
    # Internals
    ################################################################################
    def _resetTopLevelItems(self, groups: typing.Sequence[AccountGroup]):
        self._top_level_items = [None, None, None, None]

        def setTopLevelItem(account_group: AccountGroup, account_type: AccountType):
            self._top_level_items[account_group.value] = AccountTreeItem(None, account_type, account_group.name, '', None)

        if AccountGroup.Asset     in groups: setTopLevelItem(AccountGroup.Asset,     AccountType.Asset)
        if AccountGroup.Liability in groups: setTopLevelItem(AccountGroup.Liability, AccountType.Liability)
        if AccountGroup.Income    in groups: setTopLevelItem(AccountGroup.Income,    AccountType.Income)
        if AccountGroup.Expense   in groups: setTopLevelItem(AccountGroup.Expense,   AccountType.Expense)

    def _indexFromId(self, account_id: int, parent: QtCore.QModelIndex) -> QtCore.QModelIndex:
        if not parent.isValid():
            return QtCore.QModelIndex()

        if (not self.hasChildren(parent)) or (parent.flags() & QtCore.Qt.ItemFlags.ItemNeverHasChildren):
            return QtCore.QModelIndex()

        rows = self.rowCount(parent)

        for i in range(rows):
            child_index = self.index(i, 0, parent)
            child_item: AccountTreeItem = child_index.internalPointer()

            if child_item.id() == account_id:
                return child_index
            
            return self._indexFromId(account_id, child_index)
        
        return QtCore.QModelIndex()

    ################################################################################
    # Overloaded methods
    ################################################################################
    def index(self, row: int, column: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        if not parent.isValid():
            if row < 4:
                top_level_item = self._top_level_items[row]
                
                if top_level_item is not None:
                    return self.createIndex(row, column, top_level_item)
            
            return QtCore.QModelIndex()
        else:
            parent_item: AccountTreeItem = parent.internalPointer()
            child_item = parent_item.child(row)

            if child_item is None:
                return QtCore.QModelIndex()

            return self.createIndex(row, column, child_item)

    def parent(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        if not index.isValid():
            return QtCore.QModelIndex()

        child_item: AccountTreeItem = index.internalPointer()
        parent_item = child_item.parent()

        if parent_item is None:
            return QtCore.QModelIndex()
        else:
            return self.createIndex(parent_item.row(), 0, parent_item)

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if not index.isValid():
            return None
        
        if role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None

        item: AccountTreeItem = index.internalPointer()

        return item.name()

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        if not index.isValid():
            return QtCore.Qt.ItemFlag.NoItemFlags
        
        return super().flags(index)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.ItemDataRole.DisplayRole:
            # TODO: tr()
            return 'Name'

        return None

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if not parent.isValid():
            return 4
        else:
            parent_item: AccountTreeItem = parent.internalPointer()
            return parent_item.childCount()

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 1

class AccountListModel(QtCore.QAbstractListModel):
    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)

        self._accounts = []

    def select(self, extended_names: bool = True):
        with models.sql.get_session() as session:
            A      = ExtendedAccountView if extended_names else Account
            stmt   = sa.select(A.id, A.name, A.type).select_from(A)
            result = session.execute(stmt).all()

            self.layoutAboutToBeChanged.emit()
            self._accounts.clear()

            for acc in result:
                if extended_names:
                    acc_id, acc_name, acc_type = acc
                    acc_group = AccountGroup.fromAccountType(acc_type)

                    self._accounts.append(AccountInfo(acc_id, acc_group.name + ':' + acc_name, acc_type))
                else:
                    self._accounts.append(AccountInfo._make(acc))

            self._accounts.sort(key=lambda acc: acc.name)

            self.layoutChanged.emit()

    def accountFromIndex(self, index: QtCore.QModelIndex) -> typing.Optional[AccountInfo]:
        if not index.isValid():
            return None

        return self._accounts[index.row()]

    def indexFromId(self, account_id: int) -> QtCore.QModelIndex:
        for row, acc in enumerate(self._accounts):
            if acc.id == account_id:
                return self.index(row)
        
        return QtCore.QModelIndex()

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if role in (QtCore.Qt.ItemDataRole.DisplayRole, QtCore.Qt.ItemDataRole.EditRole):
            account = self._accounts[index.row()]
            return account.name
        
        return None

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._accounts)