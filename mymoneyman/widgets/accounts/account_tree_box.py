import functools
import typing
from PyQt5      import QtCore, QtWidgets
from mymoneyman import models, widgets

class AccountTreeBox(QtWidgets.QWidget):
    """Shows `AccountTreePanel`s together in a `QGroupBox`.
    
    The class `AccountTreeBox` implements a widget that shows an
    `AccountTreePanel` for each `AccountGroup`, except `AccountGroup.Equity`.

    Panels are layed out either as a list or as a grid. A list layout may be
    set with `setListLayout()` and will display the panels on top of one another.
    Namely, the panels for `AccountGroup.Asset`, `AccountGroup.Liability`,
    `AccountGroup.Income`, and `AccountGroup.Expense` are shown from top to bottom
    in that order.

    On the other hand, `setGridLayout()` sets a grid layout which will display 
    he panels side-by-side. In particular, the panels for `AccountGroup.Asset` and
    `AccountGroup.Liability` are put side-by-side on the first row, while the panels
    for `AccountGroup.Income` and `AccountGroup.Expense` are put side-by-by on the
    second row.

    See Also
    --------
    `AccountTreePanel`
    """

    currentChanged = QtCore.pyqtSignal(models.Account)
    doubleClicked  = QtCore.pyqtSignal(models.Account)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        self._asset_panel = widgets.AccountTreePanel(models.AccountGroup.Asset)
        self._asset_panel.currentChanged.connect(functools.partial(self._onPanelCurrentChanged, self._asset_panel))
        self._asset_panel.doubleClicked.connect(functools.partial(self._onPanelDoubleClicked, self._asset_panel))

        self._liability_panel = widgets.AccountTreePanel(models.AccountGroup.Liability)
        self._liability_panel.currentChanged.connect(functools.partial(self._onPanelCurrentChanged, self._liability_panel))
        self._liability_panel.doubleClicked.connect(functools.partial(self._onPanelDoubleClicked, self._liability_panel))

        self._income_panel = widgets.AccountTreePanel(models.AccountGroup.Income)
        self._income_panel.currentChanged.connect(functools.partial(self._onPanelCurrentChanged, self._income_panel))
        self._income_panel.doubleClicked.connect(functools.partial(self._onPanelDoubleClicked, self._income_panel))

        self._expense_panel = widgets.AccountTreePanel(models.AccountGroup.Expense)
        self._expense_panel.currentChanged.connect(functools.partial(self._onPanelCurrentChanged, self._expense_panel))
        self._expense_panel.doubleClicked.connect(functools.partial(self._onPanelDoubleClicked, self._expense_panel))

        self._selected_panel: typing.Optional[widgets.AccountTreePanel] = None

        self._group_box = QtWidgets.QGroupBox()
        self.setListLayout()
    
    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._group_box)
        main_layout.setContentsMargins(QtCore.QMargins())
        self.setLayout(main_layout)

    def setModel(self, model: models.AccountTableModel):
        self._model = model
        model.modelReset.connect(self._onAccountTableModelReset)

        for panel in self._panels():
            panel.setSourceModel(model)

    def refreshBalances(self):
        for panel in self._panels():
            panel.refreshBalance()

    def expandAll(self):
        for panel in self._panels():
            panel.expandAll()

    def collapseAll(self):
        for panel in self._panels():
            panel.collapseAll()

    def setListLayout(self):
        layout = self._prepareBoxLayout(QtWidgets.QBoxLayout.Direction.Down)

        if layout is None:
            return

        layout.addWidget(self._asset_panel)
        layout.addWidget(self._liability_panel)
        layout.addWidget(self._income_panel)
        layout.addWidget(self._expense_panel)

        self._group_box.setLayout(layout)

    def setGridLayout(self):
        layout = self._prepareBoxLayout(QtWidgets.QBoxLayout.Direction.LeftToRight)

        if layout is None:
            return
        
        left = QtWidgets.QVBoxLayout()
        left.addWidget(self._asset_panel)
        left.addWidget(self._income_panel)

        right = QtWidgets.QVBoxLayout()
        right.addWidget(self._liability_panel)
        right.addWidget(self._expense_panel)

        layout.addLayout(left)
        layout.addLayout(right)

        self._group_box.setLayout(layout)

    def currentAccountGroup(self) -> typing.Optional[models.AccountGroup]:
        """Returns the group of the currently selected panel, or `None` if no panel is selected."""

        if self._selected_panel is None:
            return None

        return self._selected_panel.accountGroup()

    def currentAccount(self) -> typing.Optional[models.Account]:
        """Returns the currently selected item in any of the panels, or `None` if no panel is selected."""

        if self._selected_panel is None:
            return None

        return self._selected_panel.currentAccount()

    def _panels(self) -> typing.Tuple[widgets.AccountTreePanel]:
        return (self._asset_panel, self._liability_panel, self._income_panel, self._expense_panel)

    def _prepareBoxLayout(self, desired_direction: QtWidgets.QBoxLayout.Direction) -> typing.Optional[QtWidgets.QBoxLayout]:
        """Prepares the layout of the widget `self._group_box` to change its direction.

        If the layout is `None`, creates a new layout and returns it.

        If the layout's direction is not same as `desired_direction`, cleans up the layout,
        resets it direction, and returns it.

        Otherwise, the layout is already in `desire_direction`, so this method returns `None`.
        """

        layout = self._group_box.layout()

        if layout is None:
            return QtWidgets.QBoxLayout(desired_direction)

        elif layout.direction() != desired_direction:
            while layout.count() > 0:
                layout.takeAt(0)

            layout.setDirection(desired_direction)
            
            return layout

        else:
            return None

    def _setCurrentPanel(self, panel: widgets.AccountTreePanel):
        # Check if the current item is of a different panel than the one
        # we have marked as "selected."
        if panel is not self._selected_panel:
            # If we have any panel marked as "selected", clear the selection on that panel.
            if self._selected_panel is not None:
                self._selected_panel.clearSelection()

            # Set panel of current item as the selected panel.
            self._selected_panel = panel

    @QtCore.pyqtSlot(models.Account)
    def _onPanelCurrentChanged(self, panel: widgets.AccountTreePanel, account: models.Account):
        self._setCurrentPanel(panel)
        self.currentChanged.emit(account)

    @QtCore.pyqtSlot(models.Account)
    def _onPanelDoubleClicked(self, panel: widgets.AccountTreePanel, account: models.Account):
        self._setCurrentPanel(panel)
        self.doubleClicked.emit(account)

    @QtCore.pyqtSlot()
    def _onAccountTableModelReset(self):
        most_common_currency = self._model.mostCommonCurrency()

        if most_common_currency is None:
            return

        for panel in self._panels():
            panel.setCurrency(most_common_currency)