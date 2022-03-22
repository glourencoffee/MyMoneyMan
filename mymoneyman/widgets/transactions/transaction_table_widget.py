import typing
from PyQt5      import QtCore, QtWidgets
from mymoneyman import models
from mymoneyman.widgets import common

class TransactionTableWidget(QtWidgets.QWidget):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._initWidgets()
        self._initLayouts()
    
    def _initWidgets(self):
        self._view = QtWidgets.QTableView()
        self._view.setModel(models.TransactionTableModel())

        self._view.setSelectionMode(QtWidgets.QTableView.SelectionMode.SingleSelection)
        self._view.setSelectionBehavior(QtWidgets.QTableView.SelectionBehavior.SelectRows)
        self._view.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)

        self._date_time_delegate = common.DateTimeDelegate('dd/MM/yyyy hh:mm:ss')
        self._acc_list_delegate  = common.AccountBoxDelegate()
        self._inflow_delegate    = common.SpinBoxDelegate()
        self._outflow_delegate   = common.SpinBoxDelegate()

        Column = models.TransactionTableItem.Column

        self._view.setItemDelegateForColumn(Column.Date,         self._date_time_delegate)
        self._view.setItemDelegateForColumn(Column.Transference, self._acc_list_delegate)
        self._view.setItemDelegateForColumn(Column.Inflow,       self._inflow_delegate)
        self._view.setItemDelegateForColumn(Column.Outflow,      self._outflow_delegate)

    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._view)
        
        self.setLayout(main_layout)

    def model(self) -> models.TransactionTableModel:
        return self._view.model()