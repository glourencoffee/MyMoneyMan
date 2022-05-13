import typing
from PyQt5      import QtCore, QtGui, QtWidgets
from mymoneyman import models

class AccountTreeWidget(QtWidgets.QWidget):
    """Shows an account tree.
    
    The class `AccountTreeWidget` implements a `QTreeView` that has an
    `AccountTreeProxyModel` as its model, which may be accessed by calling
    `model()`. Note that a method `setModel()` is not provided by this class,
    as it's part of its design that it always has an `AccountTreeProxyModel`
    as its model.

    The `QTreeView` child of this class is also not made available, as certain
    behaviors are required by this class. Namely, the child view is never expanded
    upon double click, its selection behavior is to always select rows, and its
    selection mode is always set for single-selection, that is, at most one row
    can be selected at a time.

    See Also
    --------
    `AccountTreeProxyModel`
    """

    currentChanged = QtCore.pyqtSignal(QtCore.QModelIndex, QtCore.QModelIndex)
    clicked        = QtCore.pyqtSignal(QtCore.QModelIndex)
    doubleClicked  = QtCore.pyqtSignal(QtCore.QModelIndex)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super(AccountTreeWidget, self).__init__(parent=parent)

        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        self._view = QtWidgets.QTreeView()
        self._view.setFont(QtGui.QFont('IPAPGothic', 11)) # TODO: make font user-defined
        self._view.setModel(models.AccountTreeProxyModel())
        self._view.setExpandsOnDoubleClick(False)
        self._view.setSelectionMode(QtWidgets.QTreeView.SelectionMode.SingleSelection)
        self._view.setSelectionBehavior(QtWidgets.QTreeView.SelectionBehavior.SelectRows)
        self._view.selectionModel().currentRowChanged.connect(self.currentChanged)
        self._view.clicked.connect(self.clicked)
        self._view.doubleClicked.connect(self.doubleClicked)

    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._view)
        main_layout.setContentsMargins(QtCore.QMargins())

        self.setLayout(main_layout)

    def model(self) -> models.AccountTreeProxyModel:
        return self._view.model()

    def setSourceModel(self, model: models.AccountTableModel):
        self.model().setSourceModel(model)

    def setHeaderHidden(self, hide: bool):
        """Hides or unhides all headers of this widget's view."""

        self._view.setHeaderHidden(hide)

    def setColumnHidden(self, column: models.AccountTreeProxyModel.Column, hide: bool):
        """Hides or unhides a column of this widget's view."""

        self._view.setColumnHidden(int(column), hide)

    def setAccountHidden(self, account: models.Account, hide: bool):
        """Hides or unhides an account item of this widget's view."""

        model = self.model()
        item  = model.itemFromAccount(account)

        if item is None:
            return

        index = model.indexFromItem(item)

        if not index.isValid():
            return

        self._view.setRowHidden(index.row(), index.parent(), hide)

    def expandAll(self):
        """Expands all indexes in this widget's view so that all items are visible."""

        self._view.expandAll()
    
    def collapseAll(self):
        """Collapses all indexes in this widget's view so that only top-level items are visible."""

        self._view.collapseAll()

    def clearSelection(self):
        """Sets an invalid index as currently selected."""

        self._view.selectionModel().clear()
    
    def currentIndex(self) -> QtCore.QModelIndex:
        """Returns the currently selected index."""

        return self._view.currentIndex()

    def currentItem(self) -> typing.Optional[models.AccountTreeProxyItem]:
        """Returns the currently selected item, or `None` if an invalid index is selected."""

        return self.item(self.currentIndex())

    def item(self, index: QtCore.QModelIndex) -> typing.Optional[models.AccountTreeProxyItem]:
        """Returns the item at `index` if index is valid, and `None` otherwise.
        
        Note that this method will never return the invisible root item
        in the underlying model, since the root item is located at an
        invalid index. To access the invisible root item, one must
        explicitly call `model().invisibleRootItem()`.
        """

        if index.isValid():
            return self.model().itemFromIndex(index)
        
        return None