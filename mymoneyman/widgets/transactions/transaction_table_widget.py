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
        delegate = common.DateTimeDelegate('dd/MM/yyyy hh:mm:ss')

        self._view = QtWidgets.QTableView()
        self._view.setModel(models.TransactionTableModel())
        self._view.setSelectionMode(QtWidgets.QTableView.SelectionMode.SingleSelection)
        self._view.setItemDelegateForColumn(1, delegate)

    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._view)
        
        self.setLayout(main_layout)

    def model(self) -> models.TransactionTableModel:
        return self._view.model()