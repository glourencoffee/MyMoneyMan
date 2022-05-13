import typing
from PyQt5      import QtCore, QtGui, QtWidgets
from mymoneyman import models, utils, widgets

class AccountTreePanel(QtWidgets.QWidget):
    """Shows an account tree and its balance on top.
    
    The class `AccountTreePanel` implements a panel widget that shows an
    `AccountTreeWidget` for a given `AccountGroup` with that group's balance
    on top.

    Note that the underlying tree is not made available, since this class
    must enfore the invariant that only one `AccountGroup` is set as the
    filter of the tree's model (`AccountTreeProxyModel.setFilterGroup()`).


    See Also
    --------
    `AccountTreeWidget`
    `AccountTreeProxyModel`
    """

    currentChanged = QtCore.pyqtSignal(models.Account)
    clicked        = QtCore.pyqtSignal(models.Account)
    doubleClicked  = QtCore.pyqtSignal(models.Account)

    def __init__(self, group: models.AccountGroup, parent: typing.Optional[QtWidgets.QWidget] = None):
        super(AccountTreePanel, self).__init__(parent=parent)

        self._currency: typing.Optional[models.Currency] = None

        self._initWidgets(group)
        self._initLayouts()

    def _initWidgets(self, group: models.AccountGroup):
        lbl_font = QtGui.QFont('IPAPGothic', 14)

        if   group == models.AccountGroup.Asset:     title = 'Assets'
        elif group == models.AccountGroup.Liability: title = 'Liabilities'
        elif group == models.AccountGroup.Income:    title = 'Income'
        elif group == models.AccountGroup.Expense:   title = 'Expense'
        elif group == models.AccountGroup.Equity:    title = 'Equity'

        self._title_lbl = QtWidgets.QLabel(title)
        self._title_lbl.setFont(lbl_font)

        self._balance_lbl = QtWidgets.QLabel()
        self._balance_lbl.setFont(lbl_font)
        
        self._tree = widgets.AccountTreeWidget()
        self._tree.model().setFilterGroup(group, visible=False)
        self._tree.currentChanged.connect(self._onTreeCurrentChanged)
        self._tree.clicked.connect(self._onTreeClicked)
        self._tree.doubleClicked.connect(self._onTreeDoubleClicked)
        self._tree.model().modelReset.connect(self.refreshBalance)

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
        main_layout.addWidget(self._tree)
        self.setLayout(main_layout)

    def setSourceModel(self, model: models.AccountTableModel):
        self._tree.setSourceModel(model)

    def setCurrency(self, currency: models.Currency):
        if currency is self._currency:
            return

        self._currency = currency
        self.refreshBalance()

    def currency(self) -> typing.Optional[models.Currency]:
        return self._currency

    def refreshBalance(self):
        if self._currency is None:
            return

        model = self._tree.model()

        balance = 0

        for row in range(model.rowCount()):
            item: models.AccountTreeProxyItem = model.itemFromIndex(model.index(row, 0))
            balance += item.cumulativeBalance(self._currency)

        self._balance_lbl.setText(self._currency.formatWithCode(balance, 2))

    def expandAll(self):
        self._tree.expandAll()
    
    def collapseAll(self):
        self._tree.collapseAll()

    def clearSelection(self):
        self._tree.clearSelection()

    def accountGroup(self) -> models.AccountGroup:
        return self._tree.model().filterGroups()[0]

    def account(self, index: QtCore.QModelIndex) -> typing.Optional[models.Account]:
        item = self._tree.item(index)

        if item is None:
            return None

        return item.account()

    def currentAccount(self) -> typing.Optional[models.Account]:
        return self.account(self._tree.currentIndex())
    
    @QtCore.pyqtSlot(QtCore.QModelIndex, QtCore.QModelIndex)
    def _onTreeCurrentChanged(self, current: QtCore.QModelIndex, previous: QtCore.QModelIndex):
        account = self.account(current)

        if account:
            self.currentChanged.emit(account)
    
    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def _onTreeClicked(self, index: QtCore.QModelIndex):
        account = self.account(index)

        if account:
            self.clicked.emit(account)

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def _onTreeDoubleClicked(self, index: QtCore.QModelIndex):
        account = self.account(index)

        if account:
            self.doubleClicked.emit(account)