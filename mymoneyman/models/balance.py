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
            # WITH cte AS (
            #   SELECT a.parent_id    AS parent_id,
            #          a.id           AS id,
            #          a.name         AS name,
            #          a.description  AS description
            #     FROM subtransaction AS s
            #     JOIN account        AS a ON s.origin_id = a.id
            #    WHERE a.type in `account_types`
            #    UNION
            #   SELECT a.parent_id    AS parent_id,
            #          a.id           AS id,
            #          a.name         AS name,
            #          a.description  AS description
            #     FROM subtransaction AS s
            #     JOIN account        AS a ON s.target_id = a.id
            #    WHERE a.type in `account_types`
            # )
            #    SELECT parent_id, id, name, description,
            #           (
            #             IFNULL((SELECT SUM(s.quantity) FROM subtransaction AS s WHERE s.target_id = cte.id GROUP BY s.target_id), 0) -
            #             IFNULL((SELECT SUM(s.quantity) FROM subtransaction AS s WHERE s.origin_id = cte.id GROUP BY s.origin_id), 0)
            #           )
            #      FROM cte
            # UNION ALL
            #    SELECT a.parent_id, a.id, a.name, a.description, 0
            #      FROM account AS a
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

            S = models.Subtransaction
            A = models.Account

            cte_stmt = sa.union(
                (
                    sa.select(A.parent_id, A.id, A.name, A.description)
                      .select_from(S)
                      .join(A, S.origin_id == A.id)
                      .where(A.type.in_(account_types))
                ),
                (
                    sa.select(A.parent_id, A.id, A.name, A.description)
                      .select_from(S)
                      .join(A, S.target_id == A.id)
                      .where(A.type.in_(account_types))
                )
            )
            
            cte = cte_stmt.cte('cte')

            origin_sum_stmt = sa.select(sa.func.sum(S.quantity)).select_from(S).where(S.origin_id == cte.c.id).group_by(S.origin_id)
            target_sum_stmt = sa.select(sa.func.sum(S.quantity)).select_from(S).where(S.target_id == cte.c.id).group_by(S.target_id)

            stmt = sa.union_all(
                (
                    sa.select(cte.c.parent_id, cte.c.id, cte.c.name, cte.c.description,
                              (
                                sa.func.ifnull(target_sum_stmt.scalar_subquery(), 0) -
                                sa.func.ifnull(origin_sum_stmt.scalar_subquery(), 0)
                              ))
                      .select_from(cte)
                ),
                (
                    sa.select(A.parent_id, A.id, A.name, A.description, sa.literal(0))
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