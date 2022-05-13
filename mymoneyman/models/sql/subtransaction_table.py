import decimal
import enum
import typing
from PyQt5        import QtCore, QtGui
from PyQt5.QtCore import Qt
from mymoneyman   import models, utils

class SubtransactionTableItem:
    __slots__ = '_subtransaction'

    def __init__(self, subtransaction: models.Subtransaction):
        self._subtransaction = subtransaction

    def subtransaction(self) -> models.Subtransaction:
        return self._subtransaction

    def flags(self) -> Qt.ItemFlags:
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def data(self) -> typing.Any:
        return None

    def font(self) -> QtGui.QFont:
        return QtGui.QFont()

    def setData(self, value: typing.Any) -> bool:
        return False

    def __str__(self) -> str:
        return str(self.data())

    def __repr__(self) -> str:
        return utils.makeRepr(
            self.__class__,
            {
                'subtransaction': self.subtransaction(),
                'data': self.data()
            }
        )

class SubtransactionTableEditableItem(SubtransactionTableItem):
    def flags(self) -> Qt.ItemFlags:
        return super().flags() | Qt.ItemFlag.ItemIsEditable

class SubtransactionTableCommentItem(SubtransactionTableEditableItem):
    def comment(self) -> str:
        return self.subtransaction().comment or ''
    
    def data(self) -> typing.Any:
        return self.comment()

    def setData(self, value: typing.Any) -> bool:
        if not isinstance(value, str):
            return False

        subtransaction = self.subtransaction()

        if subtransaction.comment == value:
            return False

        subtransaction.comment = value
        return True

    def __str__(self) -> str:
        return self.comment()

class SubtransactionTableAccountItem(SubtransactionTableEditableItem):
    __slots__ = '_account_attr'

    def __init__(self, subtransaction: models.Subtransaction, account_attr: str):
        super().__init__(subtransaction)

        self._account_attr = account_attr

    def account(self) -> typing.Optional[models.Account]:
        return getattr(self.subtransaction(), self._account_attr)
    
    def data(self) -> typing.Any:
        return self.account()

    def setData(self, value: typing.Any) -> bool:
        if not isinstance(value, models.Account):
            return False

        subtransaction = self.subtransaction()

        if getattr(subtransaction, self._account_attr) is value:
            return False

        setattr(subtransaction, self._account_attr, value)

        if (
            subtransaction.origin is not None and
            subtransaction.target is not None and
            subtransaction.origin.asset is subtransaction.target.asset
        ):
            subtransaction.quote_price = decimal.Decimal(1)

        return True

    def __str__(self) -> str:
        account = self.account()

        if account is not None:
            return account.extendedName()
        else:
            return ''

class SubtransactionTableQuantityItem(SubtransactionTableEditableItem):
    def quantity(self) -> decimal.Decimal:
        return self.subtransaction().quantity
    
    def data(self) -> typing.Any:
        return self.quantity()

    def setData(self, value: typing.Any) -> bool:
        try:
            value = decimal.Decimal(value)
        except decimal.DecimalException:
            return False

        subtransaction = self.subtransaction()

        if subtransaction.quantity == value:
            return False

        subtransaction.quantity = value
        return True

    def __str__(self) -> str:
        target_account = self.subtransaction().target
        
        if target_account is None or target_account.asset is None:
            return ''

        return target_account.asset.format(self.quantity())

class SubtransactionTableQuoteItem(SubtransactionTableEditableItem):
    def quote(self) -> decimal.Decimal:
        return self.subtransaction().quote_price
    
    def data(self) -> typing.Any:
        return self.quote()

    def flags(self) -> Qt.ItemFlags:
        subtransaction = self.subtransaction()
        origin_account = subtransaction.origin
        target_account = subtransaction.target
        
        if origin_account is None or origin_account.asset is None:
            return super().flags()

        if target_account is None or target_account.asset is None:
            return super().flags()

        if origin_account.asset is target_account.asset:
            return SubtransactionTableItem.flags(self)

        return super().flags()

    def setData(self, value: typing.Any) -> bool:
        try:
            value = decimal.Decimal(value)
        except decimal.DecimalException:
            return False

        subtransaction = self.subtransaction()

        if subtransaction.quote_price == value:
            return False

        subtransaction.quote_price = value
        return True

    def __str__(self) -> str:
        subtransaction = self.subtransaction()
        
        return subtransaction.dumpQuote()

class SubtransactionTableTotalItem(SubtransactionTableItem):
    def total(self) -> decimal.Decimal:
        subtransaction = self.subtransaction()

        return subtransaction.quantity * subtransaction.quote_price
    
    def data(self) -> typing.Any:
        return self.quote()

    def __str__(self) -> str:
        origin_account = self.subtransaction().origin
        
        if origin_account is None or origin_account.asset is None:
            return ''

        return origin_account.asset.format(self.total())

class SubtransactionTableModel(QtCore.QAbstractItemModel):
    class Column(enum.IntEnum):
        Comment  = 0
        Origin   = 1
        Target   = 2
        Quantity = 3
        Quote    = 4
        Total    = 5

    @staticmethod
    def createItemList(subtransaction: models.Subtransaction):
        return [
            SubtransactionTableCommentItem(subtransaction),
            SubtransactionTableAccountItem(subtransaction, 'origin'),
            SubtransactionTableAccountItem(subtransaction, 'target'),
            SubtransactionTableQuantityItem(subtransaction),
            SubtransactionTableQuoteItem(subtransaction),
            SubtransactionTableTotalItem(subtransaction)
        ]

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

        self._transaction = None
        self._items: typing.List[typing.List[SubtransactionTableItem]] = []

    def reset(self):
        self.beginResetModel()

        self._items.clear()

        if self._transaction is not None:
            for subtransaction in self._transaction.subtransactions:
                self._items.append(self.createItemList(subtransaction))

        self.endResetModel()

    def setTransaction(self, transaction: typing.Optional[models.Transaction]):
        if self._transaction is transaction:
            return
        
        self._transaction = transaction
        self.reset()

    def transaction(self) -> typing.Optional[models.Transaction]:
        return self._transaction

    def subtransaction(self, row: int) -> models.Subtransaction:
        return self._items[row][0].subtransaction()

    def subtransactions(self) -> typing.Generator[models.Subtransaction, None, None]:
        return (self.subtransaction(row) for row in range(self.rowCount()))

    def appendSubtransaction(self):
        if self._transaction is None:
            return

        subtransaction = models.Subtransaction(transaction = self._transaction)
        row            = self.rowCount()

        self.beginInsertRows(QtCore.QModelIndex(), row, row)
        self._items.append(self.createItemList(subtransaction))
        self.endInsertRows()

    def removeSubtransaction(self, row: int):
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        self._items.pop(row)
        self.endRemoveRows()

    def itemFromIndex(self, index: QtCore.QModelIndex) -> typing.Optional[SubtransactionTableItem]:
        return index.internalPointer()

    def emitDataChanged(self, row: int):
        self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))

    ################################################################################
    # Overriden methods (QAbstractItemModel)
    ################################################################################
    def index(self, row: int, column: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
        """Reimplements `QAbstractItemModel.index()`."""

        if parent.isValid() or row < 0 or column < 0:
            return QtCore.QModelIndex()

        try:
            item = self._items[row][column]
        except IndexError:
            return QtCore.QModelIndex()

        return self.createIndex(row, column, item)

    def parent(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        """Reimplements `QAbstractItemModel.parent()`."""

        return QtCore.QModelIndex()

    def flags(self, index: QtCore.QModelIndex) -> Qt.ItemFlags:
        """Reimplements `QAbstractItemModel.flags()`."""
        
        item = self.itemFromIndex(index)

        if item is None:
            return Qt.ItemFlag.NoItemFlags

        return item.flags()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> typing.Any:
        """Reimplements `QAbstractItemModel.headerData()`."""

        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return SubtransactionTableModel.Column(section).name

        return None

    def data(self, index: QtCore.QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> typing.Any:
        """Reimplements `QAbstractItemModel.data()`."""

        item = self.itemFromIndex(index)

        if item is not None:
            if   role == Qt.ItemDataRole.DisplayRole: return str(item)
            elif role == Qt.ItemDataRole.EditRole:    return item.data()
            elif role == Qt.ItemDataRole.FontRole:    return item.font()

        return None

    def setData(self, index: QtCore.QModelIndex, value: typing.Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """Reimplements `QAbstractItemModel.setData()`."""

        if role != Qt.ItemDataRole.EditRole:
            return False

        item = self.itemFromIndex(index)

        if item is None:
            return False

        if not item.setData(value):
            return False

        self.emitDataChanged(index.row())
        return True

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        """Reimplements `QAbstractItemModel.rowCount()`."""

        if parent.isValid():
            return 0
        
        return len(self._items)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        """Reimplements `QAbstractItemModel.columnCount()`."""

        if parent.isValid():
            return 0

        return len(SubtransactionTableModel.Column)