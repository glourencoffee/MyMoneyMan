import decimal
import enum
import sqlalchemy as sa
import typing
from PyQt5      import QtCore
from mymoneyman import models

class SubtransactionTableColumn(enum.IntEnum):
    Comment  = 0
    Origin   = 1
    Target   = 2
    Quantity = 3

class SubtransactionTableItem:
    __slots__ = (
        '_id',
        '_comment',
        '_origin',
        '_target',
        '_quantity'
    )

    def __init__(self,
                 id: typing.Optional[int],
                 comment: typing.Optional[str],
                 origin: models.AccountInfo,
                 target: models.AccountInfo,
                 quantity: decimal.Decimal
    ):
        self._id       = id
        self._comment  = comment
        self._origin   = origin
        self._target   = target
        self._quantity = quantity

    def id(self) -> typing.Optional[int]:
        """Returns the id of the subtransaction for persisted items."""

        return self._id

    def comment(self) -> typing.Optional[str]:
        """Returns the comment describing the subtransaction, if any."""

        return self._comment

    def originAccount(self) -> models.AccountInfo:
        """Returns basic information about the origin account of this subtransaction."""

        return self._origin

    def targetAccount(self) -> models.AccountInfo:
        """Returns basic information about the target account of this subtransaction."""

        return self._target

    def quantity(self) -> decimal.Decimal:
        """Returns the amount transferred from the origin account to the target account."""

        return self._quantity

    def isNew(self) -> bool:
        """Returns whether this item was created by user, as opposed to being returned from the database.
        
        All new items have a value of `None` for their `id()`, since they have not been persisted yet,
        whereas all persisted, non-new items have a value of `int` for their `id()`.
        """

        return self._id is None

    def isValid(self) -> bool:
        """Returns whether this item is in a valid state to be persisted to the database.
        
        If this item is not valid, calling `SubtransactionTableModel.persist()` on the model
        which contains this item will result in an error.
        """

        return (
            self._origin.name != '' and
            self._target.name != '' and
            self._quantity    != 0
        )

    def isEmptyComment(self) -> bool:
        """Returns whether this item's comment is `None` or an empty string."""

        return self._comment is None or self._comment == ''

    def isEmpty(self) -> bool:
        """Returns whether this item has no relevant information set, and is thus
        good to be removed.
        
        This method is used by `SubtransactionTableModel` to remove an item after
        it is changed by user, since it would be pointless to store an empty subtransaction
        on the database.
        """

        return (
            self.isEmptyComment()   and
            self._origin.name == '' and
            self._target.name == '' and
            self._quantity    == 0
        )

    def data(self, column: SubtransactionTableColumn, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if   column == SubtransactionTableColumn.Comment:  return self._comment
            elif column == SubtransactionTableColumn.Origin:   return self._origin.name
            elif column == SubtransactionTableColumn.Target:   return self._target.name
            elif column == SubtransactionTableColumn.Quantity: return str(self._quantity) if self._quantity != 0 else None
        elif role == QtCore.Qt.ItemDataRole.EditRole:
            if   column == SubtransactionTableColumn.Comment:  return self._comment
            elif column == SubtransactionTableColumn.Origin:   return self._origin.id
            elif column == SubtransactionTableColumn.Target:   return self._target.id
            elif column == SubtransactionTableColumn.Quantity: return self._quantity

        return None
    
    def setData(self, column: SubtransactionTableColumn, value: typing.Any, role: int = QtCore.Qt.ItemDataRole.EditRole) -> bool:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if   column == SubtransactionTableColumn.Origin and isinstance(value, str): self._origin = self._origin._replace(name=value)
            elif column == SubtransactionTableColumn.Target and isinstance(value, str): self._target = self._target._replace(name=value)
            else:
                return False

            return True

        elif role == QtCore.Qt.ItemDataRole.EditRole:
            if   column == SubtransactionTableColumn.Comment  and isinstance(value, str): self._comment = value
            elif column == SubtransactionTableColumn.Origin   and isinstance(value, int): self._origin = self._origin._replace(id=value)
            elif column == SubtransactionTableColumn.Target   and isinstance(value, int): self._target = self._target._replace(id=value)
            elif column == SubtransactionTableColumn.Quantity and isinstance(value, decimal.Decimal): self._quantity = round(value, 8)
            else:
                return False
            
            return True

        return False

    def __repr__(self) -> str:
        return (
            'SubtransactionTableItem<'
                f"id={self._id} "
                f"comment='{self._comment}' "
                f"origin(id={self._origin.id} name='{self._origin.name}') "
                f"target(id={self._target.id} name='{self._target.name}') "
                f'quantity={self._quantity}'
            '>'
        )

class _InsertableItem(SubtransactionTableItem):
    def __init__(self):
        account = models.AccountInfo(0, '', models.AccountType.Asset)

        super().__init__(None, '', account, account, decimal.Decimal(0))

class SubtransactionTableModel(QtCore.QAbstractTableModel):
    itemChanged = QtCore.pyqtSignal(int, SubtransactionTableItem)
    """Emitted if an item in a model is changed."""

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)

        self._items: typing.List[SubtransactionTableItem] = []
        self._removed_ids = set()
        self._transaction_id: typing.Optional[int] = None
        self._insertable_item = _InsertableItem()

    def clear(self):
        self.beginResetModel()
        
        self._items.clear()
        self._removed_ids.clear()
        self._transaction_id = None
        self._insertable_item = _InsertableItem()

        self.endResetModel()

    def select(self, transaction_id: int):
        with models.sql.get_session() as session:
            # SELECT s.id, s.comment, s.quantity,
            #        o.id, o.name, o.type,
            #        t.id, t.name, t.type
            #   FROM subtransaction        AS s
            #   JOIN extended_account_view AS o ON s.origin_id = o.id
            #   JOIN extended_account_view AS t ON s.target_id = t.id
            #  WHERE s.transaction_id = :transaction_id

            S = sa.orm.aliased(models.Subtransaction,      name='s')
            O = sa.orm.aliased(models.ExtendedAccountView, name='o')
            T = sa.orm.aliased(models.ExtendedAccountView, name='t')

            stmt = (
                sa.select(
                    S.id, S.comment, S.quantity,
                    O.id, O.name, O.type,
                    T.id, T.name, T.type
                  )
                  .select_from(S)
                  .join(O, S.origin_id == O.id)
                  .join(T, S.target_id == T.id)
                  .where(S.transaction_id == transaction_id)
            )

            results = session.execute(stmt).all()

            self.layoutAboutToBeChanged.emit()
            
            self._transaction_id = transaction_id
            self._removed_ids.clear()
            self._items.clear()

            for (
                sub_id, comment, quantity,
                origin_id, origin_name, origin_type,
                target_id, target_name, target_type
            ) in results:
                
                origin_group = models.AccountGroup.fromAccountType(origin_type)
                target_group = models.AccountGroup.fromAccountType(target_type)

                origin_acc = models.AccountInfo(origin_id, origin_group.name + ':' + origin_name, origin_type)
                target_acc = models.AccountInfo(target_id, target_group.name + ':' + target_name, target_type)

                sub_item = SubtransactionTableItem(sub_id, comment, origin_acc, target_acc, quantity)

                self._items.append(sub_item)

            self.layoutChanged.emit()

    def persist(self):
        if self._transaction_id is None:
            return

        Subtransaction = models.Subtransaction

        with models.sql.get_session() as session:
            # Delete subtransactions from removed items.
            for sub_id in self._removed_ids:
                session.execute(sa.delete(Subtransaction).where(Subtransaction.id == sub_id))

            self._removed_ids.clear()

            # Add or update items.
            for item in self._items:
                if item.isNew():
                    s = Subtransaction(
                        transaction_id = self._transaction_id,
                        comment        = item.comment(),
                        origin_id      = item.originAccount().id,
                        target_id      = item.targetAccount().id,
                        quantity       = item.quantity()
                    )

                    session.add(s)
                    item._id = s.id
                else:
                    # TODO: create "dirty" flag for subtransaction items so that we don't
                    #       have to issue update statements for subtransactions that haven't
                    #       changed at all.
                    session.execute(
                        sa.update(Subtransaction)
                          .where(Subtransaction.id == item.id())
                          .values(
                            comment   = item.comment(),
                            origin_id = item.originAccount().id,
                            target_id = item.targetAccount().id,
                            quantity  = item.quantity()
                          )
                    )
            
            session.commit()

    def removeRow(self, row: int) -> bool:
        """Removes a row from this model.
        
        If `row` is either the insertable row or not a valid row in this model, returns `False`.
        Otherwise, removes the row and returns `True`.
        """

        try:
            item = self._items[row]
        except IndexError:
            return False

        self.layoutAboutToBeChanged.emit()

        self._items.pop(row)

        # Mark subtransaction to be deleted later by `persist()` if `item` is persisted.
        if not item.isNew():
            self._removed_ids.add(item.id())

        self.layoutChanged.emit()

        return True

    def items(self) -> typing.List[SubtransactionTableItem]:
        """Returns a list of items in this model.
        
        Note that the returned list of items does not include the insertable item.
        """

        return self._items.copy()

    def itemCount(self) -> int:
        """Returns the number of items in this model.
        
        Note that the returned count does not include the insertable item.
        """

        return len(self._items)

    ################################################################################
    # Overloaded methods
    ################################################################################
    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        try:
            item: SubtransactionTableItem = self._items[index.row()]
        except IndexError:
            item = self._insertable_item

        column = SubtransactionTableColumn(index.column())

        return item.data(column, role)

    def setData(self, index: QtCore.QModelIndex, value: typing.Any, role: int = QtCore.Qt.ItemDataRole.EditRole) -> bool:
        row    = index.row()
        column = SubtransactionTableColumn(index.column())

        try:
            item: SubtransactionTableItem = self._items[row]

            if item.setData(column, value, role):
                if item.isEmpty():
                    self.layoutAboutToBeChanged.emit()
                    self._items.pop(row)
                    self.layoutChanged.emit()
                else:
                    self.dataChanged.emit(self.index(row, index.column()), self.index(row, self.columnCount() - 1))
                    self.itemChanged.emit(row, item)

                return True

            return False
        except IndexError:
            pass
        
        item = self._insertable_item

        if item.setData(column, value, role):
            if not item.isEmpty():
                self.layoutAboutToBeChanged.emit()
                self._items.append(item)
                self._insertable_item = _InsertableItem()
                self.layoutChanged.emit()

            return True
        
        return False

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        return super().flags(index) | QtCore.Qt.ItemFlag.ItemIsEditable

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.ItemDataRole.DisplayRole:
            column = SubtransactionTableColumn(section)

            return column.name

        return None

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._items) + 1

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(SubtransactionTableColumn)