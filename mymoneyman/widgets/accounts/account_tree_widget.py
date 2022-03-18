import typing
from PyQt5      import QtCore, QtGui, QtWidgets
from mymoneyman import models

class AccountTreeWidget(QtWidgets.QWidget):
    """Implements a `QtWidgets.QTreeView` based on `AccountTreeModel`."""

    itemClicked = QtCore.pyqtSignal(models.AccountTreeItem)
    """Emitted when a tree item is clicked."""

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        self._view = QtWidgets.QTreeView()
        self._view.setFont(QtGui.QFont('IPAPGothic', 11)) # TODO: make font user-defined
        self._view.setModel(models.AccountTreeModel())
        self._view.clicked.connect(self._onIndexClicked)

    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._view)
        main_layout.setContentsMargins(QtCore.QMargins())

        self.setLayout(main_layout)

    def setModel(self, model: models.AccountTreeModel):
        self._view.setModel(model)

    def setHeaderHidden(self, hide: bool):
        self._view.setHeaderHidden(hide)

    def model(self) -> models.AccountTreeModel:
        return self._view.model()
    
    def currentItem(self) -> typing.Optional[models.AccountTreeItem]:
        index = self._view.currentIndex()

        return self.model().itemFromIndex(index)

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def _onIndexClicked(self, index: QtCore.QModelIndex):
        item = self.model().itemFromIndex(index)

        self.itemClicked.emit(item)