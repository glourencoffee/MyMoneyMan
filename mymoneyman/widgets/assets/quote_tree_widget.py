import typing
from PyQt5      import QtCore, QtWidgets
from mymoneyman import models

class QuoteTreeWidget(QtWidgets.QWidget):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        self._view = QtWidgets.QTreeView()
        self._view.setModel(models.QuoteTreeModel())
    
    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._view)
        main_layout.setContentsMargins(QtCore.QMargins())
    
        self.setLayout(main_layout)

    def expandAll(self):
        self._view.expandAll()

    def collapseAll(self):
        self._view.collapseAll()

    def currentIndex(self) -> QtCore.QModelIndex:
        return self._view.currentIndex()

    def model(self) -> models.QuoteTreeModel:
        return self._view.model()