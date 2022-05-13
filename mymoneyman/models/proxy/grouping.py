from __future__ import annotations
import collections
import typing
from PyQt5        import QtCore
from PyQt5.QtCore import Qt
from mymoneyman   import utils

class GroupingProxyItem:
    __slots__ = (
        '_source_index',
        '_parent',
        '_children'
    )

    def __init__(self, source_index: QtCore.QPersistentModelIndex = QtCore.QPersistentModelIndex()):
        self._source_index = source_index
        self._parent       = None
        self._children     = []

    def isSourceIndex(self) -> bool:
        return self._source_index.isValid()

    def sourceIndex(self) -> QtCore.QModelIndex:
        return QtCore.QModelIndex(self._source_index)

    def parent(self) -> typing.Optional[GroupingProxyItem]:
        return self._parent

    def child(self, row: int) -> GroupingProxyItem:
        return self._children[row]

    def childCount(self) -> int:
        return len(self._children)
    
    def hasChildren(self) -> bool:
        return self.childCount() != 0

    def children(self) -> typing.List[GroupingProxyItem]:
        return self._children.copy()

    def findChild(self, key: typing.Callable[[GroupingProxyItem], bool]) -> typing.Optional[GroupingProxyItem]:
        for child in self._children:
            if key(child):
                return child
            
            grandchild = child.findChild(key=key)

            if grandchild is not None:
                return grandchild

        return None

    def position(self) -> int:
        if self._parent is None:
            return 0
        
        return self._parent._children.index(self)

    def __repr__(self) -> str:
        return utils.makeRepr(
            self.__class__, {
                'source_index': utils.indexLocation(self._source_index)
            }
        )

class GroupingProxyModel(QtCore.QAbstractProxyModel):
    """Groups indices of a source model.
    
    The class `GroupingProxyModel` extends `QAbstractProxyModel` to
    implement a proxy model that allows subclasses to define a grouping
    criteria so that indices of a source model may be arranged differently
    than in that source model.

    A typical use of this class is to turn a table model into a tree model.
    This may be useful for models that provide records from hierarchical
    database tables.
    """

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

        self._root_item = GroupingProxyItem()

    def reset(self):
        if self.sourceModel() is None:
            return

        self.beginResetModel()
        self.resetRoot()

        deferred_rows = collections.deque()

        for source_row in range(self.sourceModel().rowCount()):
            if not self.filterAcceptsRow(source_row):
                continue
        
            if not self.createItemForRow(source_row):
                deferred_rows.append(source_row)

        # TODO: detect recursion?
        while True:
            try:
                source_row = deferred_rows.popleft()
            except IndexError:
                break
            
            if not self.createItemForRow(source_row):
                deferred_rows.append(source_row)

        self.endResetModel()

    def invisibleRootItem(self) -> GroupingProxyItem:
        return self._root_item

    def dataForItem(self, item: GroupingProxyItem, column: int, role: int = Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if not item.isSourceIndex():
            return None

        source_model = self.sourceModel()
        source_index = source_model.index(item.sourceIndex().row(), column)

        return source_model.data(source_index, role)

    def itemFromIndex(self, proxy_index: QtCore.QModelIndex) -> GroupingProxyItem:
        """Returns the item at `proxy_index`.
        
        If `proxy_index` is invalid, returns `invisibleRootItem()`.
        Otherwise, returns the `GroupingProxyItem` at `proxy_index`.
        
        The behavior is undefined if `proxy_index` is not an index
        of this model.
        """

        if not proxy_index.isValid():
            return self._root_item
        else:
            return proxy_index.internalPointer()

    def indexFromItem(self, item: GroupingProxyItem) -> QtCore.QModelIndex:
        """Returns the index which `item` is at.
        
        If `item` is `invisibleRootItem()`, returns an invalid index.
        Otherwise, returns the index of `item` in this proxy model.

        The behavior is undefined if `item` was not created by this model.
        """

        if item is self._root_item:
            return QtCore.QModelIndex()
        else:
            return self.createIndex(item.position(), 0, item)

    ################################################################################
    # Overriden methods (QAbstractItemModel)
    ################################################################################
    def index(self, row: int, column: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
        """Reimplements `QAbstractItemModel.index()`."""

        parent_item = self.itemFromIndex(parent)
        child_item  = parent_item.child(row)

        return self.createIndex(row, column, child_item)

    def parent(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        """Reimplements `QAbstractItemModel.parent()`."""

        child_item = self.itemFromIndex(index)
        
        if child_item == self._root_item:
            return QtCore.QModelIndex()

        parent_item = child_item.parent()

        if parent_item is None or parent_item == self._root_item:
            return QtCore.QModelIndex()
        
        return self.createIndex(parent_item.position(), 0, parent_item)

    def flags(self, index: QtCore.QModelIndex) -> Qt.ItemFlags:
        """Reimplements `QAbstractItemModel.flags()`."""
        
        item = self.itemFromIndex(index)
        
        if not item.isSourceIndex():
            return Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable
        
        # Respect source model flags, but ensure that the flag
        # `Qt.ItemFlag.ItemNeverHasChildren` is never set, as
        # otherwise no child is ever shown by this proxy model.
        flags = self.sourceModel().flags(item.sourceIndex())
        flags &= ~Qt.ItemFlag.ItemNeverHasChildren

        return flags

    def data(self, index: QtCore.QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> typing.Any:
        """Reimplements `QAbstractItemModel.data()`."""

        item = self.itemFromIndex(index)

        return self.dataForItem(item, index.column(), role)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> typing.Any:
        """Reimplements `QAbstractItemModel.headerData()`."""

        if orientation == Qt.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.sourceModel().headerData(section, orientation, role)

        return None

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        """Reimplements `QAbstractItemModel.rowCount()`."""

        parent_item = self.itemFromIndex(parent)
        return parent_item.childCount()

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        """Reimplements `QAbstractItemModel.columnCount()`."""

        return self.sourceModel().columnCount()

    ################################################################################
    # Overridden methods (QAbstractProxyModel)
    ################################################################################
    def setSourceModel(self, source_model: QtCore.QAbstractItemModel):
        """Reimplements `QAbstractProxyModel.setSourceModel()`."""

        if self.sourceModel() is not None:
            self.disconnect(self.sourceModel())

        super().setSourceModel(source_model)
        
        self.sourceModel().modelReset.connect(self.reset)
        self.sourceModel().layoutChanged.connect(self.reset)
        self.sourceModel().rowsInserted.connect(self._onRowsInserted)
        self.sourceModel().rowsAboutToBeRemoved.connect(self._onSourceRowsAboutToBeRemoved)

        self.reset()

    def mapFromSource(self, source_index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        """Reimplements `QAbstractProxyModel.mapFromSource()`."""

        def key(item: GroupingProxyItem) -> bool:
            return item.sourceIndex() == source_index
        
        item = self._root_item.findChild(key=key)

        if item is None:
            return QtCore.QModelIndex()

        return self.indexFromItem(item)

    def mapToSource(self, proxy_index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        """Reimplements `QAbstractProxyModel.mapToSource()`."""

        item = self.itemFromIndex(proxy_index)

        return item.sourceIndex()

    def hasChildren(self, parent: QtCore.QModelIndex) -> bool:
        """Reimplements `QAbstractProxyModel.hasChildren()`."""

        parent_item = self.itemFromIndex(parent)
        
        return parent_item.hasChildren()

    ################################################################################
    # Internals
    ################################################################################
    def resetRoot(self):
        self._root_item = GroupingProxyItem()

    def filterAcceptsRow(self, source_row: int):
        return True

    def createItemForRow(self, source_row: int) -> bool:
        self.createItem(source_row, self._root_item)
        return True

    def createItemForIndex(self, source_index: QtCore.QPersistentModelIndex) -> GroupingProxyItem:
        return GroupingProxyItem(source_index)

    def createItem(self, source_row: int, parent_item: GroupingProxyItem) -> GroupingProxyItem:
        source_index = self.sourceModel().index(source_row, 0)
        source_index = QtCore.QPersistentModelIndex(source_index)
        
        item = self.createItemForIndex(source_index)

        self.appendItem(item, parent_item)

        return item

    def appendItem(self, item: GroupingProxyItem, parent_item: GroupingProxyItem):
        parent_item._children.append(item)
        item._parent = parent_item

    def removeItem(self, item: GroupingProxyItem):
        parent_item = item.parent()

        if parent_item is None:
            return

        try:
            parent_item._children.remove(item)
            item._parent = None
        except ValueError:
            pass

    def removeItemAtIndex(self, proxy_index: QtCore.QModelIndex):
        if not proxy_index.isValid():
            return

        self.beginRemoveRows(proxy_index.parent(), proxy_index.row(), proxy_index.row())
        self.removeItem(self.itemFromIndex(proxy_index))
        self.endRemoveRows()

    def _onRowsInserted(self, source_parent: QtCore.QModelIndex, first: int, last: int):
        self.layoutAboutToBeChanged.emit()

        while first <= last:
            if self.filterAcceptsRow(first):
                self.createItemForRow(first)

            first += 1
        
        self.layoutChanged.emit()

    def _onSourceRowsAboutToBeRemoved(self, source_parent: QtCore.QModelIndex, first: int, last: int):
        while first <= last:
            source_index = self.sourceModel().index(first, 0)
            proxy_index  = self.mapFromSource(source_index)

            if proxy_index.isValid():
                self.removeItemAtIndex(proxy_index)

            first += 1