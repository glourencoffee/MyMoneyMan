import typing
from PyQt5      import QtCore, QtGui, QtWidgets
from mymoneyman import models, utils

class BalanceTreeWidget(QtWidgets.QWidget):
    currentChanged = QtCore.pyqtSignal(models.BalanceTreeItem)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        lbl_font = QtGui.QFont('IPAPGothic', 14)

        self._title_lbl = QtWidgets.QLabel()
        self._title_lbl.setFont(lbl_font)

        self._balance_lbl = QtWidgets.QLabel()
        self._balance_lbl.setFont(lbl_font)
        
        self._view = QtWidgets.QTreeView()
        self._view.setModel(models.BalanceTreeModel())
        self._view.setSelectionMode(QtWidgets.QTreeView.SelectionMode.SingleSelection)
        self._view.setSelectionBehavior(QtWidgets.QTreeView.SelectionBehavior.SelectRows)
        self._view.selectionModel().currentRowChanged.connect(self._onCurrentRowChanged)
        self._view.setFont(QtGui.QFont('IPAPGothic', 11))

        self._group = None

    def _initLayouts(self):
        line_frame = QtWidgets.QFrame(self)
        line_frame.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line_frame.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)

        name_balance_layout = QtWidgets.QHBoxLayout()
        name_balance_layout.addWidget(self._title_lbl,   0, QtCore.Qt.AlignmentFlag.AlignLeft)
        name_balance_layout.addWidget(self._balance_lbl, 0, QtCore.Qt.AlignmentFlag.AlignRight)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(name_balance_layout)
        main_layout.addWidget(line_frame)
        main_layout.addWidget(self._view)
        self.setLayout(main_layout)
    
    def model(self) -> models.BalanceTreeModel:
        return self._view.model()

    def setTitle(self, title: str):
        self._title_lbl.setText(title)
    
    def setGroup(self, group: models.AccountGroup):
        self._group = group
        self.model().select(group)
        self._view.setColumnWidth(0, self.width() * 0.25)
        self._view.setColumnWidth(1, self.width() * 0.4)

        # TODO: use account currency
        self._balance_lbl.setText('$ ' + utils.short_format_number(self.model().totalBalance(), 2))

    def group(self) -> typing.Optional[models.AccountGroup]:
        return self._group

    def selectedItem(self) -> typing.Optional[models.BalanceTreeItem]:
        indexes = self._view.selectedIndexes()
        
        if len(indexes) == 0:
            return None
        
        return self.model().itemFromIndex(indexes[0])

    def expandAll(self):
        self._view.expandAll()
        self._view.resizeColumnToContents(0)
    
    def collapseAll(self):
        self._view.collapseAll()

    def clearSelection(self):
        self._view.selectionModel().clear()
    
    @QtCore.pyqtSlot(QtCore.QModelIndex, QtCore.QModelIndex)
    def _onCurrentRowChanged(self, current: QtCore.QModelIndex, previous: QtCore.QModelIndex):
        item = self.model().itemFromIndex(current)

        if item is not None:
            self.currentChanged.emit(item)