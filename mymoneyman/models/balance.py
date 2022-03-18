from __future__ import annotations
import collections
import decimal
import typing
import sqlalchemy as sa
from PyQt5      import QtCore
from mymoneyman import utils, models

class BalanceTreeItem:
    """Contains information of an item of `BalanceTreeModel`."""

    __slots__ = (
        '_id',
        '_name',
        '_description',
        '_balance',
        '_parent',
        '_children'
    )

    def __init__(self,
                 id: int,
                 name: str,
                 description: str,
                 balance: decimal.Decimal,
                 parent: typing.Optional[BalanceTreeItem]
    ):
        self._id          = id
        self._name        = name
        self._description = description
        self._balance     = balance
        self._parent      = parent
        self._children    = []

    def id(self) -> int:
        return self._id

    def name(self) -> str:
        return self._name

    def description(self) -> str:
        return self._description

    def balance(self) -> decimal.Decimal:
        return self._balance

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
            #    SELECT a.parent_id, a.id, a.name, a.description, SUM(t.quantity)
            #      FROM subtransaction AS t
            #      JOIN account        AS a ON t.account_id = a.id
            #     WHERE a.type in :account_types
            #  GROUP BY a.id
            # UNION ALL
            #    SELECT a.parent_id, a.id, a.name, a.description, 0
            #      FROM account AS a
            #     WHERE a.type in :account_types
            #       AND (SELECT COUNT() FROM subtransaction AS t WHERE t.account_id = a.id) = 0
            #-------------------------------------------------------------------------------
            # Explanation:
            #
            # (Select all accounts that have transactions and are in `account_types`,
            #  summing up their transactions.)
            # UNION ALL
            # (Select all accounts that have no transactions and are in `account_types`,
            #  leaving their balance as 0.)
            ################################################################################

            T = models.Subtransaction
            A = models.Account

            stmt = sa.union_all(
                (
                    sa.select(A.parent_id, A.id, A.name, A.description, sa.func.sum(T.quantity))
                      .select_from(T)
                      .join(A, T.account_id == A.id)
                      .where(A.type.in_(account_types))
                      .group_by(A.id)
                ),
                (
                    sa.select(A.parent_id, A.id, A.name, A.description, sa.literal(0))
                      .where(A.type.in_(account_types))
                      .where(
                            sa.select(sa.func.count())
                              .where(T.account_id == A.id)
                              .scalar_subquery() == 0
                        )
                )
            )

            for t in session.execute(stmt).all():
                parent_id, id, name, desc, balance = t

                balance_info[parent_id].append((id, name, desc, balance))

        self.layoutAboutToBeChanged.emit()
        self._resetRootItem()

        try:
            def read_recursive(item: BalanceTreeItem):
                try:
                    info_list = balance_info.pop(item.id())
                except KeyError:
                    return

                for id, name, desc, balance in info_list:
                    child = BalanceTreeItem(id, name, desc, balance, item)
                    
                    item.appendChild(child)
                    read_recursive(child)

            top_level_list = balance_info.pop(None)

            for id, name, desc, balance in top_level_list:
                child = BalanceTreeItem(id, name, desc, balance, self._root_item)
                read_recursive(child)

                self._root_item.appendChild(child)

        except KeyError:
            pass
            
        self.layoutChanged.emit()

    def totalBalance(self) -> decimal.Decimal:
        return sum(top_level_item.balance() for top_level_item in self._root_item.children())

    def itemFromIndex(self, index: QtCore.QModelIndex) -> typing.Optional[BalanceTreeItem]:
        if not index.isValid():
            return None

        return index.internalPointer()

    ################################################################################
    # Internals
    ################################################################################
    def _resetRootItem(self):
        self._root_item = BalanceTreeItem(0, '', '', 0, None)

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
        if role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None

        item = self.itemFromIndex(index)

        if item is None:
            return None
        
        column = index.column()

        if   column == 0: return item.name()
        elif column == 1: return item.description()
        elif column == 2:
            # TODO: maybe move summing logic to query when having to deal with currency rates.
            total_balance = item.balance() + sum(child.balance() for child in item.children())

            return  utils.short_format_number(total_balance, 2)
        else:
            return None

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        if not index.isValid():
            return QtCore.Qt.ItemFlags.NoItemFlags
        
        return super().flags(index)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.ItemDataRole.DisplayRole:
            return ('Name', 'Description', 'Balance')[section]

        return None

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item: BalanceTreeItem = parent.internalPointer()

        return parent_item.childCount()

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 3