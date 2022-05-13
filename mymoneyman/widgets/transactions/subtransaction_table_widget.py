import typing
from PyQt5      import QtCore, QtWidgets
from mymoneyman import models, widgets

class SubtransactionTableWidget(QtWidgets.QWidget):
    def __init__(self, model: models.AccountTableModel, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

        self._origin_account_delegate = widgets.AccountComboDelegate(model)
        self._target_account_delegate = widgets.AccountComboDelegate(model)
        self._quantity_delegate       = widgets.SpinBoxDelegate()
        self._quote_delegate          = widgets.SpinBoxDelegate()

        self._initWidgets()
        self._initLayouts()
    
    def _initWidgets(self):
        self._view = QtWidgets.QTableView()
        self._view.setModel(models.SubtransactionTableModel())
        self._view.setSelectionMode(QtWidgets.QTableView.SelectionMode.SingleSelection)
        self._view.setSelectionBehavior(QtWidgets.QTableView.SelectionBehavior.SelectRows)
        self._view.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.AllEditTriggers)

        Column = models.SubtransactionTableModel.Column

        self._view.setItemDelegateForColumn(Column.Origin,   self._origin_account_delegate)
        self._view.setItemDelegateForColumn(Column.Target,   self._target_account_delegate)
        self._view.setItemDelegateForColumn(Column.Quantity, self._quantity_delegate)
        self._view.setItemDelegateForColumn(Column.Quote,    self._quote_delegate)

    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._view)
        main_layout.setContentsMargins(QtCore.QMargins())

        self.setLayout(main_layout)

    def model(self) -> models.SubtransactionTableModel:
        return self._view.model()

    def currentIndex(self) -> QtCore.QModelIndex:
        return self._view.currentIndex()

    def resizeColumnsToContents(self):
        self._view.resizeColumnsToContents()

    @QtCore.pyqtSlot()
    def _onModelLayoutChanged(self):
        self.resizeColumnsToContents()