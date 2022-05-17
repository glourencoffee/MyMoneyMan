import decimal
import enum
import typing
from PyQt5        import QtCore, QtGui
from PyQt5.QtCore import Qt
from mymoneyman   import models, utils

class TransactionProxyItem:
    __slots__ = (
        '_source_index_or_transaction',
        '_account'
    )

    def __init__(self,
                 source_index_or_transaction: typing.Union[
                     QtCore.QPersistentModelIndex,
                     models.Transaction
                 ],
                 account: models.Account
    ):
        self._source_index_or_transaction = source_index_or_transaction
        self._account = account

    def account(self) -> models.Account:
        return self._account

    def sourceIndex(self) -> QtCore.QModelIndex:
        if not isinstance(self._source_index_or_transaction, QtCore.QPersistentModelIndex):
            return QtCore.QModelIndex()

        return QtCore.QModelIndex(self._source_index_or_transaction)

    def transaction(self) -> models.Transaction:
        if isinstance(self._source_index_or_transaction, models.Transaction):
            return self._source_index_or_transaction

        source_index = QtCore.QModelIndex(self._source_index_or_transaction)
        source_model: models.TransactionTableModel = source_index.model()

        return source_model.transaction(source_index.row())

    def subtransaction(self) -> models.Subtransaction:
        transaction = self.transaction()

        try:
            return transaction.subtransactions[0]
        except IndexError:
            subtransaction = models.Subtransaction(
                transaction = transaction,
                origin      = self.account()
            )

            return subtransaction

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
                'source_index': utils.indexLocation(self.sourceIndex()),
                'account': self.account().extendedName(),
                'data': self.data()
            }
        )

class TransactionProxyEditableItem(TransactionProxyItem):
    def flags(self) -> Qt.ItemFlags:
        flags = super(TransactionProxyEditableItem, self).flags()

        if not self.transaction().isSplit():
            flags |= Qt.ItemFlag.ItemIsEditable
        
        return flags

class TransactionProxyTypeItem(TransactionProxyItem):
    def type(self) -> models.TransactionType:
        return self.transaction().type()
    
    def data(self) -> typing.Any:
        return self.type()

    def font(self) -> QtGui.QFont:
        font = super(TransactionProxyTypeItem, self).font()
        font.setItalic(True)

        return font

    def __str__(self) -> str:
        if self.sourceIndex().isValid():
            return self.type().name
        
        return 'New'

class TransactionProxyDateItem(TransactionProxyEditableItem):
    def date(self) -> QtCore.QDateTime:
        transaction = self.transaction()

        if transaction.date is not None:
            return QtCore.QDateTime(transaction.date)
        else:
            return QtCore.QDateTime.currentDateTime()

    def flags(self) -> Qt.ItemFlags:
        return TransactionProxyItem.flags(self) | Qt.ItemFlag.ItemIsEditable

    def data(self) -> typing.Any:
        return self.date()

    def setData(self, value: typing.Any) -> bool:
        if not isinstance(value, QtCore.QDateTime):
            return False
        
        transaction = self.transaction()
        new_date    = value.toPyDateTime()

        if transaction.date == new_date:
            return False

        transaction.date = new_date
        return True

    def __str__(self) -> str:
        return self.date().toString('dd/MM/yyyy hh:mm:ss')


class TransactionProxyCommentItem(TransactionProxyEditableItem):
    def comment(self) -> str:
        return self.subtransaction().comment or ''
    
    def data(self) -> typing.Any:
        return self.comment()

    def font(self) -> QtGui.QFont:
        font = super(TransactionProxyCommentItem, self).font()
        font.setItalic(self.transaction().isSplit())

        return font

    def setData(self, value: typing.Any) -> bool:
        if not isinstance(value, str):
            return False

        subtransaction = self.subtransaction()

        if subtransaction.comment == value:
            return False

        subtransaction.comment = value
        return True

    def __str__(self) -> str:
        if self.transaction().isSplit():
            return '-- Split Transaction --'
        
        return self.comment()

class TransactionProxyTransferenceItem(TransactionProxyEditableItem):
    def transferenceAccount(self) -> typing.Optional[models.Account]:
        subtransaction = self.subtransaction()

        if   self.account() is subtransaction.origin: return subtransaction.target
        elif self.account() is subtransaction.target: return subtransaction.origin
        else:
            return None

    def data(self) -> typing.Any:
        return self.transferenceAccount()

    def font(self) -> QtGui.QFont:
        font = super(TransactionProxyTransferenceItem, self).font()
        font.setItalic(self.transaction().isSplit())

        return font

    def setData(self, value: typing.Any) -> bool:
        if not isinstance(value, models.Account):
            return False

        subtransaction = self.subtransaction()
            
        if self.account() is subtransaction.origin:
            subtransaction.target = value
        else:
            subtransaction.origin = value

        return True
    
    def __str__(self) -> str:
        if self.transaction().isSplit():
            return '-- Many --'
        
        transference_account = self.transferenceAccount()
        
        if transference_account is not None:
            return transference_account.extendedName()
        
        return ''

class TransactionProxyInflowItem(TransactionProxyEditableItem):
    def quantity(self) -> typing.Optional[decimal.Decimal]:
        quantity = self.transaction().relativeQuantity(self.account())

        return quantity if quantity > 0 else None

    def data(self) -> typing.Any:
        return self.quantity()
    
    def setData(self, value: typing.Any) -> bool:
        if not isinstance(value, (float, int, str, tuple, decimal.Decimal)):
            return False

        if self.transaction().isSplit():
            return False

        new_quantity   = decimal.Decimal(value)
        subtransaction = self.subtransaction()

        is_inflow = self.account() is subtransaction.target

        if is_inflow:
            if new_quantity >= 0:
                subtransaction.quantity = new_quantity
            else:
                subtransaction.quantity = abs(new_quantity)
                subtransaction.swap()
        else:
            if new_quantity <= 0:
                subtransaction.quantity += abs(new_quantity) / subtransaction.quote_price
            else:
                subtransaction.quantity -= new_quantity / subtransaction.quote_price

                if subtransaction.quantity <= 0:
                    subtransaction.quantity = abs(subtransaction.quantity)
                    subtransaction.swap()

        return True
    
    def __str__(self) -> str:
        quantity = self.quantity()
        
        if quantity is not None:
            return str(quantity)
        else:
            return ''

class TransactionProxyOutflowItem(TransactionProxyEditableItem):
    def setData(self, value: typing.Any) -> bool:
        return False

    def quantity(self) -> typing.Optional[decimal.Decimal]:
        quantity = self.transaction().relativeQuantity(self.account())

        return -quantity if quantity < 0 else None

    def data(self) -> typing.Any:
        return self.quantity()

    def setData(self, value: typing.Any) -> bool:
        if not isinstance(value, (float, int, str, tuple, decimal.Decimal)):
            return False

        if self.transaction().isSplit():
            return False

        new_quantity   = decimal.Decimal(value)
        subtransaction = self.subtransaction()

        is_outflow = self.account() is subtransaction.origin

        if is_outflow:
            new_quantity /= subtransaction.quote_price

            if new_quantity >= 0:
                subtransaction.quantity = new_quantity
            else:
                subtransaction.quantity = abs(new_quantity)
                subtransaction.swap()
        else:
            if new_quantity <= 0:
                subtransaction.quantity += abs(new_quantity)
            else:
                subtransaction.quantity -= new_quantity

                if subtransaction.quantity <= 0:
                    subtransaction.quantity = abs(subtransaction.quantity)
                    subtransaction.swap()

        return True

    def __str__(self) -> str:
        quantity = self.quantity()
        
        if quantity is not None:
            return str(quantity)
        else:
            return ''

class TransactionProxyBalanceItem(TransactionProxyItem):
    __slots__ = '_balance'

    def __init__(self, source_index: QtCore.QPersistentModelIndex, account: models.Account):
        super().__init__(source_index, account)

        self._balance = decimal.Decimal(0)

    def balance(self) -> decimal.Decimal:
        account   = self.account()
        precision = account.precision or account.asset.precision

        return round(self._balance, precision)

    def data(self) -> typing.Any:
        return self.balance()

    def font(self) -> QtGui.QFont:
        font = super().font()
        font.setBold(True)

        return font

    def setData(self, value: typing.Any) -> bool:
        if not isinstance(value, decimal.Decimal):
            return False

        if self._balance == value:
            return False

        self._balance = value
        return True
    
    def __str__(self) -> str:
        return str(self.balance())

class TransactionProxyModel(QtCore.QAbstractItemModel):
    """Shows the transactions of an account.

    The class `TransactionProxyModel` implements a proxy model that filters
    transactions in `TransactionTableModel` for a given account.

    Note that this class does not extend from `QAbstractProxyModel`,
    directly but from `QAbstractItemModel`. 
    
    See Also
    --------
    `TransactionTableModel`
    """

    """Implements a model for manipulating transactions on the database.
    
    This class is designed to work with one account at a time. As such, it only
    deals with transaction operations for that account. The id of the associated
    account, if any, is given by `accountId()`.

    The method `selectAccount()` retrieves transactions related to a particular
    account and stores them in the model. Information about each transaction may
    be accessed by calling `data()`, or changed by calling `setData()`.

    Beside an account's transactions, this class also provides the ability to
    insert transactions on the associated account. An instance of this class can
    be made insertable or non-insertable by calling `setInsertable()`.
    
    An insertable model will enable a *draft row*, which is a row that allows a
    draft transaction to be created.
    
    A *draft transaction* is a non-persisted transaction that may be accessed and
    modified with `data()` and `setData()`, respectively, as with any transaction.
    However, a draft transaction is NOT persisted until `persistDraft()` is called.
    A draft transaction may also be discard with `discardDraft()`, in which case a
    draft row will be reset to its original state. To check whether this model has
    an active draft transaction, call `hasDraft()`.
    """

    class Column(enum.IntEnum):
        Type          = 0
        Date          = 1
        Comment       = 2
        Transference  = 3
        Inflow        = 4
        Outflow       = 5
        Balance       = 6

    def __init__(self, account: typing.Optional[models.Account] = None, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

        self._account      = account
        self._source_model = None
        self._items: typing.List[typing.List[TransactionProxyItem]] = []
        self._insertable: bool = False

    def reset(self):
        self.beginResetModel()

        transaction_model: models.TransactionTableModel = self.sourceModel()

        self._items.clear()

        if self._account is not None:
            for row, transaction in enumerate(transaction_model.transactions()):
                if not self.filterAcceptsTransaction(transaction):
                    continue

                source_index = transaction_model.index(row, 0)
                source_index = QtCore.QPersistentModelIndex(source_index)

                self._items.append(self.createItemList(source_index))

            self._items.sort(key=lambda item_list: item_list[0].transaction().date)

            if self._insertable:
                self._items.append(self.createItemList(models.Transaction()))

            self.recalculateBalances()

        self.endResetModel()

    def setAccount(self, account: typing.Optional[models.Account]):
        if self._account is account:
            return

        self._account = account
        self.reset()

    def account(self) -> typing.Optional[models.Account]:
        return self._account

    def isInsertable(self) -> bool:
        return self._insertable

    def setInsertable(self, insertable: bool):
        """
        
        If this model is not insertable, it can only be made insertable if it has an
        `account()` associated with it. If `account()` is `None`, does nothing.
        """

        if insertable == self.isInsertable():
            return

        if insertable:
            if self._account is None:
                return

            row = self.rowCount()

            self.beginInsertRows(QtCore.QModelIndex(), row, row)
            self._items.append(self.createItemList(models.Transaction()))
            self.endInsertRows()
        else:
            row = self.rowCount() - 1

            self.beginRemoveRows(QtCore.QModelIndex(), row, row)
            self._items.pop(row)
            self.endRemoveRows()

        self._insertable = insertable

    def isInsertableRow(self, row: int) -> bool:
        return self.isInsertable() and row == (self.rowCount() - 1)

    def persist(self, row: int):
        transaction = self.transaction(row)
        transaction_model: models.TransactionTableModel = self.sourceModel()

        is_insertable_row = self.isInsertableRow(row)

        print('persist(): row ==', row)

        if not transaction_model.upsert(transaction):
            return

        print('persisted!!')
        
        print('transaction:', transaction)

        transaction_date = transaction.date
        transaction_row  = row

        # Find the row where the transaction is supposed to be at.
        # The supposed row may be different from the one the transaction
        # is currently at, if `Transaction.date` has been changed or whether
        # `transaction` is a new one (meaning, it is at the insertable row).
        if is_insertable_row or transaction.hasChanged('date'):
            for item_row, item_list in enumerate(self._items):
                if self.isInsertableRow(item_row):
                    continue

                item_transaction = item_list[0].transaction()

                print('item_row ==', item_row, 'item_transaction ==', item_transaction)

                if transaction is item_transaction:
                    continue

                if transaction_date < item_transaction.date:
                    transaction_row = item_row
                    break
        
        if transaction_row != row:
            print('transaction_row != row; transaction_row ==', transaction_row)
            
            # Start a moving operation for the transaction to its supposed row.
            self.beginMoveRows(
                QtCore.QModelIndex(), row, row,
                QtCore.QModelIndex(), transaction_row
            )

            item_list = self._items.pop(row)

            if transaction_row > row:
                # We just popped an item from `row` in the items list,
                # and `transaction_row` is "below" `row`, which means we
                # must decrease one row from `transaction_row`, since
                # the item list has one item less.
                transaction_row -= 1
            
            self._items.insert(transaction_row, item_list)

            self.endMoveRows()
        else:
            print('transaction_row == row')
            # There's no need to move rows, so simply notify data changes.
            self.emitDataChanged(transaction_row)

        if is_insertable_row:
            print('is_insertable_row')
            # An insertable row was inserted into the database.
            # Create a new insertable row at the end of the items list.

            row = self.rowCount()

            self.beginInsertRows(QtCore.QModelIndex(), row, row)
            self._items.append(self.createItemList(models.Transaction()))
            self.endInsertRows()
        
        self.recalculateBalances()

    def discard(self, row: int):
        transaction = self.transaction(row)

        if self.isInsertableRow(row):
            transaction.date = QtCore.QDateTime.currentDateTime().toPyDateTime()
            transaction.subtransactions.clear()
        else:
            transaction.refresh()

        self.emitDataChanged(row)
        self.recalculateBalances()

    def transaction(self, row: int) -> models.Transaction:
        return self._items[row][0].transaction()

    def transactions(self) -> typing.Generator[models.Transaction, None, None]:
        return (self.transaction(row) for row in range(self.rowCount()))

    def filterAcceptsTransaction(self, transaction: models.Transaction) -> bool:
        for sub in transaction.subtransactions:
            if sub.origin is self._account or sub.target is self._account:
                return True
        
        return False

    def setSourceModel(self, model: QtCore.QAbstractItemModel):
        if not isinstance(model, models.TransactionTableModel):
            raise TypeError('model is not instance of TransactionTableModel')

        self._source_model = model
        
        model.rowsAboutToBeRemoved.connect(self._onSourceRowsAboutToBeRemoved)

        self.reset()

    def sourceModel(self) -> QtCore.QAbstractItemModel:
        return self._source_model

    def itemFromIndex(self, index: QtCore.QModelIndex) -> typing.Optional[TransactionProxyItem]:
        """
        Returns the `TransactionProxyItem` at `index` if `index`
        is valid, and `None` otherwise.
        """

        return index.internalPointer()

    def emitDataChanged(self, row: int):
        """Emits the signal `dataChanged` for all columns except `Column.Balance`.
        
        Data for items at `Column.Balance` are only changed by `recalculateBalances()`.
        """

        Column = TransactionProxyModel.Column

        self.dataChanged.emit(
            self.index(row, int(Column.Type)),
            self.index(row, int(Column.Balance) - 1)
        )

    def recalculateBalances(self, first_row: int = 0):
        """Recalculates balances for all rows starting at `first_row`.
        
        
        """

        item_count = len(self._items)

        if first_row < 0 or first_row >= item_count:
            return

        balance_column = int(TransactionProxyModel.Column.Balance)

        if first_row == 0:
            balance = decimal.Decimal(0)
        else:
            balance_item: TransactionProxyBalanceItem = self._items[first_row - 1][balance_column]
            balance = balance_item.balance()

        for i in range(first_row, item_count):
            item_list = self._items[i]

            balance_item: TransactionProxyBalanceItem = item_list[balance_column]
            
            account  = balance_item.account()
            quantity = balance_item.transaction().relativeQuantity(account)

            # Reverse the balance for inflow account groups.
            if quantity != 0 and account.group().isInflow():
                quantity *= -1

            balance += quantity
            balance_item.setData(balance)
        
        self.dataChanged.emit(self.index(first_row, balance_column), self.index(self.rowCount() - 1, balance_column))

    def createItemList(self, source_model_or_transaction: typing.Union[QtCore.QPersistentModelIndex, models.Transaction]):
        """Creates an item list to be stored by this model."""

        items = []
        items.append(TransactionProxyTypeItem(source_model_or_transaction, self._account))
        items.append(TransactionProxyDateItem(source_model_or_transaction, self._account))
        items.append(TransactionProxyCommentItem(source_model_or_transaction, self._account))
        items.append(TransactionProxyTransferenceItem(source_model_or_transaction, self._account))
        items.append(TransactionProxyInflowItem(source_model_or_transaction, self._account))
        items.append(TransactionProxyOutflowItem(source_model_or_transaction, self._account))
        items.append(TransactionProxyBalanceItem(source_model_or_transaction, self._account))

        return items

    ################################################################################
    # Overriden methods (QAbstractItemModel)
    ################################################################################
    def index(self, row: int, column: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
        """Reimplements `QAbstractItemModel.index()`."""

        if parent.isValid() or row < 0 or column < 0:
            return QtCore.QModelIndex()

        item = self._items[row][column]

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
            return TransactionProxyModel.Column(section).name

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

        if item.setData(value):
            self.emitDataChanged(index.row())

            Column = TransactionProxyModel.Column
            column = Column(index.column())

            # Recalculate balances for this row and all subsequent rows if
            # data has changed in any of the following columns.
            if column in (Column.Transference, Column.Inflow, Column.Outflow):
                self.recalculateBalances(index.row())

            return True
        
        return False

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        """Reimplements `QAbstractItemModel.rowCount()`."""

        if parent.isValid():
            return 0
        
        return len(self._items)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        """Reimplements `QAbstractItemModel.columnCount()`."""

        if parent.isValid():
            return 0

        return len(TransactionProxyModel.Column)
    
    @QtCore.pyqtSlot(QtCore.QModelIndex, int, int)
    def _onSourceRowsAboutToBeRemoved(self, parent: QtCore.QModelIndex, first: int, last: int):
        row = first

        while row <= last:
            source_index = self.sourceModel().index(row, 0)
            proxy_item   = None
            proxy_row    = None

            for item_row, item_list in enumerate(self._items):
                item = item_list[0]

                if item.sourceIndex() == source_index:
                    proxy_item = item
                    proxy_row  = item_row
                    break
            
            if proxy_item is not None:
                self.beginRemoveRows(QtCore.QModelIndex(), proxy_row, proxy_row)
                self._items.pop(proxy_row)
                self.endRemoveRows()
            
            row += 1