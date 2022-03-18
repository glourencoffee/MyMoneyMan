import functools
import typing
from PyQt5              import QtCore, QtWidgets
from mymoneyman.widgets import accounts as widgets
from mymoneyman         import models

class BalanceBox(QtWidgets.QWidget):
    currentChanged = QtCore.pyqtSignal(widgets.BalanceTreeWidget, models.BalanceTreeItem)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        # TODO: tr()
        self._asset_tree = widgets.BalanceTreeWidget()
        self._asset_tree.setTitle('Assets')
        self._asset_tree.setGroup(models.AccountGroup.Asset)
        self._asset_tree.currentChanged.connect(functools.partial(self._onTreeCurrentChanged, self._asset_tree))

        self._liability_tree = widgets.BalanceTreeWidget()
        self._liability_tree.setTitle('Liabilities')
        self._liability_tree.setGroup(models.AccountGroup.Liability)
        self._liability_tree.currentChanged.connect(functools.partial(self._onTreeCurrentChanged, self._liability_tree))

        self._income_tree = widgets.BalanceTreeWidget()
        self._income_tree.setTitle('Income')
        self._income_tree.setGroup(models.AccountGroup.Income)
        self._income_tree.currentChanged.connect(functools.partial(self._onTreeCurrentChanged, self._income_tree))

        self._expense_tree = widgets.BalanceTreeWidget()
        self._expense_tree.setTitle('Expenses')
        self._expense_tree.setGroup(models.AccountGroup.Expense)
        self._expense_tree.currentChanged.connect(functools.partial(self._onTreeCurrentChanged, self._expense_tree))

        self._selected_tree = None

        self._tree_group_box = QtWidgets.QGroupBox()
        self.setListLayout()
    
    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._tree_group_box)
        main_layout.setContentsMargins(QtCore.QMargins())
        self.setLayout(main_layout)

    def expandAll(self):
        for tree in self._trees():
            tree.expandAll()

    def collapseAll(self):
        for tree in self._trees():
            tree.collapseAll()

    def setListLayout(self):
        layout = self._prepareBoxLayout(QtWidgets.QBoxLayout.Direction.Down)

        if layout is None:
            return

        layout.addWidget(self._asset_tree)
        layout.addWidget(self._liability_tree)
        layout.addWidget(self._income_tree)
        layout.addWidget(self._expense_tree)

        self._tree_group_box.setLayout(layout)

    def setGridLayout(self):
        layout = self._prepareBoxLayout(QtWidgets.QBoxLayout.Direction.LeftToRight)

        if layout is None:
            return
        
        left = QtWidgets.QVBoxLayout()
        left.addWidget(self._asset_tree)
        left.addWidget(self._income_tree)

        right = QtWidgets.QVBoxLayout()
        right.addWidget(self._liability_tree)
        right.addWidget(self._expense_tree)

        layout.addLayout(left)
        layout.addLayout(right)

        self._tree_group_box.setLayout(layout)
    
    def updateBalances(self, group: models.AccountGroup):
        T = models.AccountGroup

        if   group == T.Asset:     model = self._asset_tree.model()
        elif group == T.Liability: model = self._liability_tree.model()
        elif group == T.Income:    model = self._income_tree.model()
        elif group == T.Expense:   model = self._expense_tree.model()
        else:
            return

        model.select(group)

    def selectedGroup(self) -> typing.Optional[models.AccountGroup]:
        if self._selected_tree is None:
            return None

        return self._selected_tree.group()

    def selectedItem(self) -> typing.Optional[models.BalanceTreeItem]:
        if self._selected_tree is None:
            return None

        return self._selected_tree.selectedItem()

    def _trees(self) -> typing.Tuple[widgets.BalanceTreeWidget]:
        return (self._asset_tree, self._liability_tree, self._income_tree, self._expense_tree)

    def _prepareBoxLayout(self, desired_direction: QtWidgets.QBoxLayout.Direction) -> typing.Optional[QtWidgets.QBoxLayout]:
        """Prepares the layout of the widget `self._tree_group_box` to change its direction.

        If the layout is `None`, creates a new layout and returns it.

        If the layout's direction is not same as `desired_direction`, cleans up the layout,
        resets it direction, and returns it.

        Otherwise, the layout is already in `desire_direction`, so this method returns `None`.
        """

        layout = self._tree_group_box.layout()

        if layout is None:
            return QtWidgets.QBoxLayout(desired_direction)

        elif layout.direction() != desired_direction:
            while layout.count() > 0:
                layout.takeAt(0)

            layout.setDirection(desired_direction)
            
            return layout

        else:
            return None

    @QtCore.pyqtSlot(models.BalanceTreeItem)
    def _onTreeCurrentChanged(self, tree: widgets.BalanceTreeWidget, item: models.BalanceTreeItem):
        if tree is self._selected_tree:
            return

        if self._selected_tree is not None:
            self._selected_tree.clearSelection()

        self._selected_tree = tree

        self.currentChanged.emit(tree, item)