from __future__ import annotations
import collections
import decimal
import enum
import typing
import sqlalchemy as sa
from PyQt5      import QtCore
from mymoneyman import utils, models

class BalanceTreeColumn(enum.IntEnum):
    Name        = 0
    Description = 1
    Balance     = 2

class BalanceTreeItem:
    """Contains information of an item of `BalanceTreeModel`."""

    __slots__ = (
        '_id',
        '_type',
        '_name',
        '_description',
        '_asset_id',
        '_asset_code',
        '_asset_symbol',
        '_currency_prec',
        '_balance',
        '_parent',
        '_children'
    )

    def __init__(self,
                 id: int,
                 type: models.AccountType,
                 name: str,
                 description: str,
                 asset_id: int,
                 asset_code: str,
                 asset_symbol: typing.Optional[str],
                 currency_precision: int,
                 balance: decimal.Decimal,
                 parent: typing.Optional[BalanceTreeItem]
    ):
        self._id            = id
        self._type          = type
        self._name          = name
        self._description   = description
        self._asset_id      = asset_id
        self._asset_code    = asset_code
        self._asset_symbol  = asset_symbol
        self._currency_prec = currency_precision
        self._balance       = balance
        self._parent        = parent
        self._children      = []

    def id(self) -> int:
        return self._id

    def type(self) -> models.AccountType:
        return self._type

    def name(self) -> str:
        return self._name

    def description(self) -> str:
        return self._description

    def assetId(self) -> int:
        return self._asset_id

    def assetCode(self) -> str:
        return self._asset_code

    def assetSymbol(self) -> typing.Optional[str]:
        return self._asset_symbol

    def currencyPrecision(self) -> int:
        return self._currency_prec

    def balance(self) -> decimal.Decimal:
        return self._balance

    def cumulativeBalance(self) -> decimal.Decimal:
        balance = self._balance

        for child in self._children:
            balance += child.cumulativeBalance()
        
        return balance

    def parent(self) -> typing.Optional[BalanceTreeItem]:
        return self._parent

    def children(self) -> typing.List[BalanceTreeItem]:
        return self._children.copy()

    def appendChild(self, child: BalanceTreeItem):
        self._children.append(child)

    def child(self, row: int) -> typing.Optional[BalanceTreeItem]:
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

    def data(self, column: BalanceTreeColumn, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None

        if   column == BalanceTreeColumn.Name:        return self._name
        elif column == BalanceTreeColumn.Description: return self._description
        elif column == BalanceTreeColumn.Balance:
            balance = utils.short_format_number(self.balance(), self._currency_prec)

            if self._asset_symbol:
                return f'{self._asset_symbol} {balance}'
            else:
                return f'{balance} {self._asset_code}'
        
        return None

    def __repr__(self) -> str:
        if self._parent is None:
            parent_name = None
        else:
            parent_name = f"'{self._parent._name}'"

        children_names = tuple(child._name for child in self._children)

        return (
            f"BalanceTreeItem<id={self._id} name='{self._name}' balance={self._balance}"
            f" parent={parent_name} children={children_names}>"
        )

def queryCurrencyQuote(session, base_currency_code: str, quote_currency_code: str, two_way: bool = False) -> typing.Optional[decimal.Decimal]:
    #   SELECT s.quote_price
    #     FROM subtransaction     AS s  
    #     JOIN "transaction"      AS t      ON s.transaction_id = t.id
    #     JOIN account_asset_view AS target ON s.target_id      = target.account_id
    #     JOIN account_asset_view AS origin ON s.origin_id      = origin.account_id
    #    WHERE target.asset_code = :base_currency_code
    #      AND origin.asset_code = :quote_currency_code
    #      AND target.asset_is_currency
    #      AND origin.asset_is_currency
    # ORDER BY t.date DESC
    #    LIMIT 1

    S      = sa.orm.aliased(models.Subtransaction,   name='s')
    T      = sa.orm.aliased(models.Transaction,      name='t')
    Target = sa.orm.aliased(models.AccountAssetView, name='target')
    Origin = sa.orm.aliased(models.AccountAssetView, name='origin')

    stmt = (
        sa.select(S.quote_price)
          .select_from(S)
          .join(T,      S.transaction_id == T.id)
          .join(Target, S.target_id      == Target.account_id)
          .join(Origin, S.origin_id      == Origin.account_id)
          .where(Target.asset_code == base_currency_code)
          .where(Origin.asset_code == quote_currency_code)
          .where(Target.asset_is_currency == True)
          .where(Origin.asset_is_currency == True)
          .order_by(T.date.desc())
          .limit(1)
    )

    result = session.execute(stmt).one_or_none()

    if result is not None:
        quote_price = decimal.Decimal(result[0])    
        return quote_price

    if two_way:
        quote_price = queryCurrencyQuote(session, quote_currency_code, base_currency_code, two_way=False)

        if quote_price is not None:
            return 1 / quote_price
    
    return None

def querySecurityQuote(session, base_security_id: int, quote_currency_code: str) -> typing.Optional[decimal.Decimal]:
    #   SELECT s.quote_price, target.currency_code
    #     FROM subtransaction     AS s  
    #     JOIN "transaction"      AS t      ON s.transaction_id = t.id
    #     JOIN account_asset_view AS target ON s.target_id      = target.account_id
    #     JOIN account_asset_view AS origin ON s.origin_id      = origin.account_id
    #    WHERE target.asset_id      = :base_security_id
    #      AND target.asset_type    = 'S'
    #      AND target.currency_code = origin.currency_code
    # ORDER BY t.date DESC
    #    LIMIT 1

    S      = sa.orm.aliased(models.Subtransaction,   name='s')
    T      = sa.orm.aliased(models.Transaction,      name='t')
    Target = sa.orm.aliased(models.AccountAssetView, name='target')
    Origin = sa.orm.aliased(models.AccountAssetView, name='origin')

    stmt = (
        sa.select(S.quote_price, Target.currency_code)
          .select_from(S)
          .join(T,      S.transaction_id == T.id)
          .join(Target, S.target_id      == Target.account_id)
          .join(Origin, S.origin_id      == Origin.account_id)
          .where(Target.asset_id          == base_security_id)
          .where(Target.asset_is_currency == False)
          .where(Target.currency_code     == Origin.currency_code)
          .order_by(T.date.desc())
          .limit(1)
    )

    result = session.execute(stmt).one_or_none()

    if result is None:
        return None

    quote_price   = decimal.Decimal(result[0])
    currency_code = result[1]

    if currency_code == quote_currency_code:
        return quote_price

    exchange_rate = queryCurrencyQuote(session, currency_code, quote_currency_code, two_way=True)

    if exchange_rate is not None:
        return quote_price * exchange_rate

    return None

def queryAccountBalance(account_id: int, session) -> decimal.Decimal:
    #    SELECT s.quantity, s.quote_price, -1 AS side
    #      FROM subtransaction AS s
    #      JOIN account        AS a ON s.origin_id = a.id
    #     WHERE a.id = :account_id
    # UNION ALL 
    #    SELECT s.quantity, 1 AS quote_price, 1 AS side
    #      FROM subtransaction AS s
    #      JOIN account        AS a ON s.target_id = a.id
    #     WHERE a.id = :account_id
    
    S = sa.orm.aliased(models.Subtransaction, name='s')
    A = sa.orm.aliased(models.Account,        name='a')

    s1 = (
        sa.select(S.quantity, S.quote_price, sa.literal(-1).label('side'))
          .select_from(S)
          .join(A, S.origin_id == A.id)
          .where(A.id == account_id)
    )

    s2 = (
        sa.select(S.quantity, sa.literal(1).label('quote_price'), sa.literal(1).label('side'))
          .select_from(S)
          .join(A, S.target_id == A.id)
          .where(A.id == account_id)
    )

    stmt    = s1.union_all(s2)
    results = session.execute(stmt).all()

    balance = decimal.Decimal(0)

    for quantity, quote_price, side in results:
        quantity    = decimal.Decimal(quantity) * side
        quote_price = decimal.Decimal(quote_price)
        balance     += quantity * quote_price

    return balance

class BalanceTreeModel(QtCore.QAbstractItemModel):
    """
    Implements a read-only model that stores information about the balance of account
    and account groups.
    """

    __slots__ = '_root_item'

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)

        self._resetRootItem()

    def reset(self):
        self.layoutAboutToBeChanged.emit()
        self._resetRootItem()
        self.layoutChanged.emit()

    def select(self, group: models.AccountGroup):
        balance_info = collections.defaultdict(list)

        account_types = group.accountTypes()

        with models.sql.get_session() as session:
            ################################################################################
            # WITH cte AS (
            #   SELECT a.parent_id          AS parent_id,
            #          a.id                 AS id,
            #          a.type               AS type,
            #          a.name               AS name,
            #          a.description        AS description,
            #          v.asset_id           AS asset_id,
            #          v.asset_code         AS asset_code,
            #          v.asset_symbol       AS asset_symbol,
            #          v.currency_precision AS currency_precision
            #     FROM subtransaction     AS s
            #     JOIN account            AS a ON s.origin_id = a.id
            #     JOIN account_asset_view AS v ON a.id = v.account_id
            #    WHERE a.type in `account_types`
            #    UNION
            #   SELECT a.parent_id          AS parent_id,
            #          a.id                 AS id,
            #          a.type               AS type,
            #          a.name               AS name,
            #          a.description        AS description,
            #          v.asset_id           AS asset_id,
            #          v.asset_code         AS asset_code,
            #          v.asset_symbol       AS asset_symbol,
            #          v.currency_precision AS currency_precision
            #     FROM subtransaction     AS s
            #     JOIN account            AS a ON s.target_id = a.id
            #     JOIN account_asset_view AS v ON a.id = v.account_id
            #    WHERE a.type in `account_types`
            # )
            #    SELECT parent_id, id, type, name, description,
            #           asset_id, asset_code, asset_symbol, currency_precision
            #      FROM cte
            # UNION ALL
            #    SELECT a.parent_id, a.id, a.type, a.name, a.description,
            #           v.asset_id, v.asset_code, v.asset_symbol, v.currency_precision
            #      FROM account            AS a
            #      JOIN account_asset_view AS v ON a.id = v.account_id
            #     WHERE a.type in `account_types`
            #       AND (SELECT COUNT() FROM subtransaction AS t WHERE t.origin_id = a.id) = 0
            #       AND (SELECT COUNT() FROM subtransaction AS t WHERE t.target_id = a.id) = 0
            #----------------------------------------------------------------------------------
            # Query explanation:
            # 
            # WITH cte AS (
            #   Select all accounts that:
            #    1) have transactions; and
            #    2) are in the origin side of their transactions; and
            #    3) are in `account_types`
            #   UNION
            #   Select all accounts that:
            #    1) have transactions; and
            #    2) are in the target side of their transactions; and
            #    3) are in `account_types`
            # )
            # Select account information and calculate their balance from `cte`
            # UNION ALL
            # Select all accounts that have no transactions and are in `account_types`,
            # leaving their balance as 0.
            #----------------------------------------------------------------------------------
            # Technical explanation:
            #
            # `cte` will give information about ALL accounts that have transactions. From
            # that, we calculate their balance by subtracting the account's inflow and outflow.
            #
            # Then, we retrieve accounts that have no transactions by looking up accounts
            # that are neither an origin account nor a target account for any transaction.
            #
            # All the accounts retrieved are filtered according to `account_types`.
            ################################################################################

            S = sa.orm.aliased(models.Subtransaction,   name='s')
            A = sa.orm.aliased(models.Account,          name='a')
            V = sa.orm.aliased(models.AccountAssetView, name='v')

            cte_stmt = sa.union(
                (
                    sa.select(
                        A.parent_id, A.id, A.type, A.name, A.description,
                        V.asset_id, V.asset_code, V.asset_symbol, V.currency_precision
                      )
                      .select_from(S)
                      .join(A, S.origin_id == A.id)
                      .join(V, A.id == V.account_id)
                      .where(A.type.in_(account_types))
                ),
                (
                    sa.select(
                        A.parent_id, A.id, A.type, A.name, A.description,
                        V.asset_id, V.asset_code, V.asset_symbol, V.currency_precision
                      )
                      .select_from(S)
                      .join(A, S.target_id == A.id)
                      .join(V, A.id == V.account_id)
                      .where(A.type.in_(account_types))
                )
            )
            
            cte = cte_stmt.cte('cte')

            stmt = cte.select().union_all(
                sa.select(
                    A.parent_id, A.id, A.type, A.name, A.description, 
                    V.asset_id, V.asset_code, V.asset_symbol, V.currency_precision
                )
                .select_from(A)
                .join(V, A.id == V.account_id)
                .where(A.type.in_(account_types))
                .where(
                    sa.select(sa.func.count())
                    .select_from(S)
                    .where(S.origin_id == A.id)
                    .scalar_subquery() == 0
                )
                .where(
                    sa.select(sa.func.count())
                    .select_from(S)
                    .where(S.target_id == A.id)
                    .scalar_subquery() == 0
                )
            )

            AccountGroup = models.AccountGroup

            for t in session.execute(stmt).all():
                parent_id    = t[0]
                account_id   = t[1]
                account_type = t[2]
                
                account_group = AccountGroup.fromAccountType(account_type)
                balance       = queryAccountBalance(account_id, session)

                if account_group in (AccountGroup.Equity, AccountGroup.Income, AccountGroup.Liability) and balance != 0:
                    balance *= -1

                all_but_first = t[1:]
                balance_info[parent_id].append((*all_but_first, balance))

        self.layoutAboutToBeChanged.emit()
        self._resetRootItem()

        try:
            def read_recursive(parent_item: BalanceTreeItem):
                try:
                    info_list = balance_info.pop(parent_item.id())
                except KeyError:
                    return

                for info in info_list:
                    child = BalanceTreeItem(*info, parent_item)

                    with models.sql.get_session() as session:
                        if child.type() == models.AccountType.Security:
                            quote = querySecurityQuote(session, child.assetId(), parent_item.assetCode())
                        else:
                            quote = None
                            # quote = queryCurrencyQuote(base_currency_code, quote_currency_code, session)

                        if quote is not None:
                            parent_item._balance += quote * child.balance()
                    
                    
                    parent_item.appendChild(child)
                    read_recursive(child)

            top_level_list = balance_info.pop(None)

            for info in top_level_list:
                child = BalanceTreeItem(*info, self._root_item)
                read_recursive(child)

                self._root_item.appendChild(child)

        except KeyError:
            pass
            
        self.layoutChanged.emit()

    def totalBalance(self, quote_currency_code: str = 'USD') -> decimal.Decimal:
        balance = decimal.Decimal(0)

        with models.sql.get_session() as session:
            for child in self._root_item.children():
                if child.type() == models.AccountType.Security:
                    print(f'LOOKING UP QUOTE (SECURITY ID = {child.assetId()})/{quote_currency_code}')
                    quote_price = querySecurityQuote(session, child.assetId(), quote_currency_code)
                else:
                    if child.assetCode() == quote_currency_code:
                        balance += child.balance()
                        continue
                    else:
                        print(f'LOOKING UP QUOTE in pairs {child.assetCode()}/{quote_currency_code} and {quote_currency_code}/{child.assetCode()}')
                        quote_price = queryCurrencyQuote(session, child.assetCode(), quote_currency_code, two_way=True)

                        print('RESULT:', quote_price)

                if quote_price is not None:
                    balance += child.balance() * quote_price

        return balance

    def itemFromIndex(self, index: QtCore.QModelIndex) -> typing.Optional[BalanceTreeItem]:
        if not index.isValid():
            return None

        return index.internalPointer()

    ################################################################################
    # Internals
    ################################################################################
    def _resetRootItem(self):
        self._root_item = BalanceTreeItem(0, models.AccountType.Equity, '', '', 0, '', None, 0, 0, None)

    ################################################################################
    # Overloaded methods
    ################################################################################
    def index(self, row: int, column: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        if not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item: BalanceTreeItem = parent.internalPointer()
        
        child_item = parent_item.child(row)

        if child_item is None:
            return QtCore.QModelIndex()

        return self.createIndex(row, column, child_item)

    def parent(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        child_item = self.itemFromIndex(index)

        if child_item is None:
            return QtCore.QModelIndex()

        parent_item = child_item.parent()

        if parent_item == self._root_item:
            return QtCore.QModelIndex()
        else:
            return self.createIndex(parent_item.row(), 0, parent_item)

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        item = self.itemFromIndex(index)

        if item is None:
            return None
        
        return item.data(BalanceTreeColumn(index.column()), role)

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        if not index.isValid():
            return QtCore.Qt.ItemFlags.NoItemFlags
        
        return super().flags(index)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.ItemDataRole.DisplayRole:
            return BalanceTreeColumn(section).name

        return None

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item: BalanceTreeItem = parent.internalPointer()

        return parent_item.childCount()

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(BalanceTreeColumn)