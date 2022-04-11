from __future__ import annotations
import decimal
import enum
import sqlalchemy as sa
import typing
from PyQt5      import QtCore
from mymoneyman import models

class QuoteTreeColumn(enum.IntEnum):
    First  = 0
    Second = 1
    Source = 2

class QuoteSource(enum.IntEnum):
    Transaction = 0
    Provider    = 1
    User        = 2

class QuoteTreeItem:
    __slots__ = (
        '_parent',
        '_children',
        '_text'
    )

    def __init__(self, text: str = '', parent: typing.Optional[QuoteTreeItem] = None):
        self._text     = text
        self._parent   = parent
        self._children = []

        if parent:
            parent._addChild(self)

    def text(self) -> str:
        return self._text

    def parent(self) -> typing.Optional[QuoteTreeItem]:
        return self._parent

    def children(self) -> typing.List[QuoteTreeItem]:
        return self._children.copy()

    def child(self, row: int) -> QuoteTreeItem:
        return self._children[row]

    def childCount(self) -> int:
        return len(self._children)

    def row(self) -> int:
        if self._parent is None:
            return 0

        return self._parent._children.index(self)

    def _addChild(self, child: QuoteTreeItem):
        self._children.append(child)

    def data(self, column: QuoteTreeColumn, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole and column == QuoteTreeColumn.First:
            return self._text

        return None

    def flags(self, column: QuoteTreeColumn) -> QtCore.Qt.ItemFlags:
        return QtCore.Qt.ItemFlag.ItemIsEnabled|QtCore.Qt.ItemFlag.ItemIsSelectable

class QuoteTreeQuoteItem(QuoteTreeItem):
    __slots__ = ('_date', '_price', '_source')

    def __init__(self, parent: 'QuoteTreeAssetItem', date: QtCore.QDateTime, price: decimal.Decimal, source: QuoteSource):
        super().__init__(parent=parent)

        self._date  = date
        self._price = price
        self._source = source

    def asset(self) -> 'QuoteTreeAssetItem':
        return self.parent()

    def date(self) -> QtCore.QDateTime:
        return self._date

    def price(self) -> decimal.Decimal:
        return self._price

    def source(self) -> QuoteSource:
        return self._source

    def data(self, column: QuoteTreeColumn, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if   column == QuoteTreeColumn.First:  return self._date.toString('dd/MM/yyyy hh:mm:ss')
            elif column == QuoteTreeColumn.Second: return str(self._price)
            elif column == QuoteTreeColumn.Source: return self._source.name

        return None

    def flags(self, column: QuoteTreeColumn) -> QtCore.Qt.ItemFlags:
        flags = super().flags(column)

        if column != QuoteTreeColumn.Source and self._source == QuoteSource.User:
            flags |= QtCore.Qt.ItemFlag.ItemIsEditable

        return flags

class QuoteTreeAssetItem(QuoteTreeItem):
    __slots__ = (
        '_basset_code',
        '_basset_name',
        '_qasset_code',
        '_qasset_name'
    )

    def __init__(self,
                 parent: 'QuoteTreeScopeItem',
                 base_asset_code: str,
                 base_asset_name: str,
                 quote_asset_code: str,
                 quote_asset_name: str,
    ):
        super().__init__(parent=parent)

        self._basset_code = base_asset_code
        self._basset_name = base_asset_name
        self._qasset_code = quote_asset_code
        self._qasset_name = quote_asset_name

    def scope(self) -> 'QuoteTreeScopeItem':
        return self.parent()

    def baseAssetCode(self) -> str:
        return self._basset_code

    def baseAssetName(self) -> str:
        return self._basset_name

    def quoteAssetCode(self) -> str:
        return self._qasset_code

    def quoteAssetName(self) -> str:
        return self._qasset_code

    def quoteItems(self) -> typing.List[QuoteTreeQuoteItem]:
        return self.children()

    def data(self, column: QuoteTreeColumn, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if   column == QuoteTreeColumn.First:  return self._basset_code + '/' + self._qasset_code
            elif column == QuoteTreeColumn.Second: return self._basset_name + ' vs ' + self._qasset_name
            
        return None

class QuoteTreeScopeItem(QuoteTreeItem):
    def __init__(self, parent: QuoteTreeItem, name: str):
        super().__init__(name, parent)

    def name(self) -> str:
        return self.text()

    def assetItems(self) -> typing.List[QuoteTreeAssetItem]:
        return self.children()

class QuoteTreeModel(QtCore.QAbstractItemModel):
    """Provides data of currency and security quotes stored in the database."""

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)

        self._root_item = QuoteTreeItem()

    def clear(self):
        if self._root_item.childCount() == 0:
            return

        self.beginResetModel()
        self._root_item = QuoteTreeItem()
        self.endResetModel()

    def select(self):
        with models.sql.get_session() as session:
            ################################################################################
            #   SELECT IFNULL(target.asset_scope, target.asset_code) AS scope_name,
            #          target.asset_is_currency,
            #          target.asset_code, target.asset_name,
            #          origin.asset_code, origin.asset_name,
            #          t.date, s.quote_price
            #     FROM subtransaction     AS s
            #     JOIN "transaction"      AS t      ON s.transaction_id = t.id
            #     JOIN account_asset_view AS target ON s.target_id      = target.account_id
            #     JOIN account_asset_view AS origin ON s.origin_id      = origin.account_id
            #    WHERE target.asset_is_currency == FALSE
            #       OR target.asset_id != origin.asset_id
            #       OR s.quote_price != '1'
            # ORDER BY IFNULL(target.asset_scope, target.asset_code),
            #          target.asset_code,
            #          origin.asset_code
            #-------------------------------------------------------------------------------
            # Technical explanation:
            #
            # Query information of all subtransactions where either:
            # 1. The target account is a security; or
            # 2. The assets of the target account and the origin account are different from
            #    each other; or
            # 3. The assets of the target account and the origin account are not different,
            #    but the subtransaction's quote price is not 1.
            #
            # Item 2 is meant to filter out subtransactions made between currency accounts
            # in the same denomination, such as a transference from a USD account to another
            # USD account. Had they not been filtered out, the query would return entries
            # such as USD/USD and EUR/EUR.
            #
            # Item 3 is meant to spot possible bugs. By convention, subtransactions between
            # accounts in the same denomination have the value of 1 for their quote prices.
            # That is, all USD/USD subtransactions, for example, must have the value of 1
            # as their quote price. This is a constraint that must be enforced at the
            # application level, but it's possible that the database contains a value other
            # than 1, which would be wrong. Thus, by also retrieving these incorrect quotes,
            # one may spot a possible discrepancy in balance easier than would be otherwise.
            ################################################################################

            S      = sa.orm.aliased(models.Subtransaction,   name='s')
            T      = sa.orm.aliased(models.Transaction,      name='t')
            Target = sa.orm.aliased(models.AccountAssetView, name='target')
            Origin = sa.orm.aliased(models.AccountAssetView, name='origin')

            stmt = (
                sa.select(
                    sa.func.ifnull(Target.asset_scope, Target.asset_code),
                    Target.asset_is_currency,
                    Target.asset_code, Target.asset_name,
                    Origin.asset_code, Origin.asset_name,
                    T.date,
                    S.quote_price
                )
                .select_from(S)
                .join(T,      S.transaction_id == T.id)
                .join(Target, S.target_id      == Target.account_id)
                .join(Origin, S.origin_id      == Origin.account_id)
                .where(sa.or_(
                    Target.asset_is_currency == False,
                    Target.asset_code != Origin.asset_code,
                    S.quote_price != sa.literal(1)
                ))
                .order_by(sa.func.ifnull(Target.asset_scope, Target.asset_code), Target.asset_code, Origin.asset_code)
            )

            results = session.execute(stmt).all()

            self.clear()
            
            if len(results) == 0:
                return

            self.layoutAboutToBeChanged.emit()

            currency_item = QuoteTreeItem('Currencies', self._root_item)
            security_item = QuoteTreeItem('Securities', self._root_item)

            scope_item: typing.Optional[QuoteTreeScopeItem] = None

            for (
                scope_name, base_asset_is_currency,
                base_asset_code, base_asset_name,
                quote_asset_code, quote_asset_name,
                quote_date, quote_price
            ) in results:

                if scope_item is None or scope_item.name() != scope_name:
                    if base_asset_is_currency:
                        scope_item = QuoteTreeScopeItem(currency_item, scope_name)
                    else:
                        scope_item = QuoteTreeScopeItem(security_item, scope_name)

                asset_item = None

                for item in scope_item.assetItems():
                    if item.baseAssetCode() == base_asset_code and item.quoteAssetCode() == quote_asset_code:
                        asset_item = item
                        break

                if asset_item is None:
                    asset_item = QuoteTreeAssetItem(scope_item, base_asset_code, base_asset_name, quote_asset_code, quote_asset_name)

                QuoteTreeQuoteItem(asset_item, QtCore.QDateTime(quote_date), quote_price, QuoteSource.Transaction)

            self.layoutChanged.emit()

    def itemFromIndex(self, index: QtCore.QModelIndex) -> QuoteTreeItem:
        return index.internalPointer()

    ################################################################################
    # Overloaded methods
    ################################################################################
    def index(self, row: int, column: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        if not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = self.itemFromIndex(parent)
        
        try:
            child_item = parent_item.child(row)
            return self.createIndex(row, column, child_item)
        except IndexError:
            return QtCore.QModelIndex()

    def parent(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        if not index.isValid():
            return QtCore.QModelIndex()

        child_item  = self.itemFromIndex(index)
        parent_item = child_item.parent()

        if parent_item == self._root_item:
            return QtCore.QModelIndex()
        else:
            return self.createIndex(parent_item.row(), 0, parent_item)

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        item = self.itemFromIndex(index)

        return item.data(QuoteTreeColumn(index.column()), role)

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        if not index.isValid():
            return QtCore.Qt.ItemFlags.NoItemFlags
        
        item = self.itemFromIndex(index)

        return item.flags(QuoteTreeColumn(index.column()))

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.ItemDataRole.DisplayRole:
            return QuoteTreeColumn(section).name

        return None

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item: QuoteTreeItem = parent.internalPointer()
        
        return parent_item.childCount()

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(QuoteTreeColumn)