from __future__ import annotations
import enum
import typing
from PyQt5        import QtCore
from PyQt5.QtCore import Qt
from mymoneyman   import models, utils

class SecurityTreeProxyItem(models.GroupingProxyItem):
    """Represents an item in `SecurityTreeProxyModel`.
    
    The class `SecurityTreeProxyItem` extends `GroupingProxyItem` to allow market
    items to be stored in the proxy model. Since market items are not part of a
    source model, such items always returns `False` for `isSourceIndex()`.

    See Also
    --------
    `SecurityTreeProxyModel`
    """

    __slots__ = '_market'

    def __init__(self, source_index_or_market: typing.Union[QtCore.QPersistentModelIndex, str]):
        if isinstance(source_index_or_market, str):
            source_index = QtCore.QPersistentModelIndex()
            self._market = source_index_or_market
        else:
            source_index = source_index_or_market
            self._market = None

        super().__init__(source_index)

    def isMarket(self) -> bool:
        return self._market is not None

    def security(self) -> typing.Optional[models.Security]:
        """Returns the account's id if this item is an account, and `None` otherwise."""

        if self.isSourceIndex():
            source_index = self.sourceIndex()
            source_model: models.SecurityTableModel = source_index.model()

            return source_model.security(source_index.row())

        return None
    
    def market(self) -> str:
        security = self.security()

        if security is None:
            return self._market
        else:
            return security.market

    def code(self) -> str:
        security = self.security()

        if security is None:
            return self._market
        else:
            return security.code
    
    def childCodes(self) -> typing.List[str]:
        return [child.code() for child in self.children() if isinstance(child, SecurityTreeProxyItem)]

    def __repr__(self) -> str:
        parent = self.parent()

        if isinstance(parent, SecurityTreeProxyItem):
            parent_code = "'" + parent.code() + "'"
        else:
            parent_code = None

        return utils.makeRepr(
            self.__class__,
            {
                'source_index': utils.indexLocation(self.sourceIndex()),
                'market':       self.market(),
                'code':         self.code(),
                'parent':       parent_code,
                'children':     self.childCodes()
            }
        )

class SecurityTreeProxyModel(models.GroupingProxyModel):
    """Models securities in a tree structure.
    
    The class `SecurityTreeProxyModel` extends `GroupingProxyModel` to implement
    a proxy model that arranges securities in a tree structure, which has a depth
    of at most two levels.
    
    The first level contains security markets, while the second level has securities
    grouped by market. For example, suppose that the database has the following
    securities with the markets "NASDAQ" and "BVMF" (the stock exchange in Brazil):

    | Market | Code  | Name            |
    |--------|-------|-----------------|
    | NASDAQ | AAPL  | Apple           |
    | NASDAQ | MSFT  | Microsoft       |
    | NASDAQ | GOOG  | Google          |
    | BVMF   | BBAS3 | Banco do Brasil |
    | BVMF   | ABEV3 | Ambev           |

    This model will structure these securities the following way:

    - BVMF
      - ABEV3
      - BBAS3
    - NASDAQ
      - AAPL
      - GOOG
      - MSFT

    Notice that both the market and security levels are ordered alphabetically.
    This model will ensure that items are layed out in an alphabetic order at
    all times.

    See Also
    --------
    `SecurityTableModel`
    """

    class Column(enum.IntEnum):
        """Enumerates columns used by this model class."""

        Code     = 0
        Name     = 1
        ISIN     = 2
        Type     = 3
        Currency = 4

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

    def itemFromMarket(self, market: str) -> typing.Optional[SecurityTreeProxyItem]:
        """Returns the item of this model that represents `market`."""

        for child in self.invisibleRootItem().children():
            assert isinstance(child, SecurityTreeProxyItem)
            assert child.isMarket()

            if child.market() == market:
                return child

        return None
    
    def itemFromSecurity(self, security: models.Security) -> typing.Optional[SecurityTreeProxyItem]:
        """Returns the item of this model that represents `security`."""

        return self.invisibleRootItem().findChild(lambda item: item.security() is security)

    ################################################################################
    # Overriden methods (QAbstractItemModel)
    ################################################################################
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> typing.Any:
        """Reimplements `QAbstractItemModel.headerData()`."""

        if orientation == Qt.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return SecurityTreeProxyModel.Column(section).name

        return None

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        """Reimplements `QAbstractItemModel.columnCount()`."""

        return len(SecurityTreeProxyModel.Column)

    ################################################################################
    # Overriden methods (QAbstractProxyModel)
    ################################################################################
    def setSourceModel(self, source_model: QtCore.QAbstractItemModel):
        """Reimplements `QAbstractProxyModel.setSourceModel()`."""

        if not isinstance(source_model, models.SecurityTableModel):
            raise TypeError('source model is not an instance of SecurityTableModel')

        super().setSourceModel(source_model)

    ################################################################################
    # Overriden methods (GroupingProxyModel)
    ################################################################################
    def filterAcceptsRow(self, source_row: int):
        """Reimplements `GroupingProxyModel.filterAcceptsRow()`."""

        return True

    def createItemForRow(self, source_row: int) -> bool:
        """Reimplements `GroupingProxyModel.createItemForRow()`."""

        security_table: models.SecurityTableModel = self.sourceModel()
        security = security_table.security(source_row)

        market_item = self.itemFromMarket(security.market)

        if market_item is None:
            market_item = SecurityTreeProxyItem(security.market)
            self.appendItem(market_item, self.invisibleRootItem())
        
        self.createItem(source_row, market_item)
        return True

    def createItemForIndex(self, source_index: QtCore.QPersistentModelIndex) -> models.GroupingProxyItem:
        """Reimplements `GroupingProxyModel.createItemForIndex()`."""

        return SecurityTreeProxyItem(source_index)

    def removeItemAtIndex(self, proxy_index: QtCore.QModelIndex):
        """Reimplements `GroupingProxyModel.removeItemAtIndex()`."""

        if not proxy_index.isValid():
            return

        security_item: models.SecurityTreeProxyItem = self.itemFromIndex(proxy_index)
        market_item = security_item.parent()

        if market_item.childCount() == 1:
            # print('should remove market item cuz it has no children anymore:', market_item, 'position:', market_item.position())
            self.beginRemoveRows(QtCore.QModelIndex(), market_item.position(), market_item.position())
            self.removeItem(market_item)
            self.endRemoveRows()
        else:
            super().removeItemAtIndex(proxy_index)

    def dataForItem(self, item: models.GroupingProxyItem, column: int, role: int = Qt.ItemDataRole.DisplayRole) -> typing.Any:
        """Reimplements `GroupingProxyModel.dataForItem()`."""

        if role != Qt.ItemDataRole.DisplayRole:
            return None
        
        assert isinstance(item, SecurityTreeProxyItem)

        Column = SecurityTreeProxyModel.Column
        column = Column(column)

        security = item.security()

        if security is None:
            if column == Column.Code:
                return item.market()
        else:
            if   column == Column.Code:     return security.code
            elif column == Column.Name:     return security.name
            elif column == Column.ISIN:     return security.isin
            elif column == Column.Type:     return security.security_type.name
            elif column == Column.Currency: return security.currency.code

        return None