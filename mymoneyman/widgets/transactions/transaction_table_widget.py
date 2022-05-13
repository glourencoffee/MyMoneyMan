import typing
from PyQt5      import QtCore, QtGui, QtWidgets
from mymoneyman import models, widgets

class TransactionTableWidget(QtWidgets.QWidget):
    currentRowChanged = QtCore.pyqtSignal(int, int)
    transactionChanged = QtCore.pyqtSignal(int, models.Transaction)

    def __init__(self, model: models.AccountTableModel, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

        self._initWidgets(model)
        self._initLayouts()

        self.resizeColumns()
    
    def _initWidgets(self, model: models.AccountTableModel):
        self._view = QtWidgets.QTableView()
        self._view.setModel(models.TransactionProxyModel())
        self._view.model().dataChanged.connect(self._onModelDataChanged)
        self._view.model().modelReset.connect(self.resizeColumns)
        
        self._view.setSelectionMode(QtWidgets.QTableView.SelectionMode.SingleSelection)
        self._view.setSelectionBehavior(QtWidgets.QTableView.SelectionBehavior.SelectRows)
        self._view.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
        self._view.setAlternatingRowColors(True)

        self._date_time_delegate = widgets.DateTimeDelegate('dd/MM/yyyy hh:mm:ss')
        self._acc_list_delegate  = widgets.AccountComboDelegate(model)
        self._inflow_delegate    = widgets.SpinBoxDelegate()
        self._outflow_delegate   = widgets.SpinBoxDelegate()

        Column = models.TransactionProxyModel.Column

        self._view.setItemDelegateForColumn(Column.Date,         self._date_time_delegate)
        self._view.setItemDelegateForColumn(Column.Transference, self._acc_list_delegate)
        self._view.setItemDelegateForColumn(Column.Inflow,       self._inflow_delegate)
        self._view.setItemDelegateForColumn(Column.Outflow,      self._outflow_delegate)

        self._view.selectionModel().currentRowChanged.connect(self._onCurrentRowChanged)

        p = self.palette()
        p.setColor(QtGui.QPalette.ColorRole.Highlight,       QtGui.QColor('#48aa99'))
        p.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtCore.Qt.white)
        self.setPalette(p)

    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._view)
        main_layout.setContentsMargins(QtCore.QMargins())
        
        self.setLayout(main_layout)

    def currentIndex(self) -> QtCore.QModelIndex:
        return self._view.currentIndex()

    def currentRow(self) -> int:
        index = self._view.currentIndex()
        
        if index.isValid():
            return index.row()
        
        return -1

    def currentTransaction(self) -> typing.Optional[models.Transaction]:
        current_row = self.currentRow()

        if current_row == -1:
            return None

        return self.model().transaction(current_row)

    def model(self) -> models.TransactionProxyModel:
        return self._view.model()

    def item(self, index: QtCore.QModelIndex) -> models.TransactionProxyItem:
        return self.model().itemFromIndex(index)

    def resizeColumns(self):
        Column = models.TransactionProxyModel.Column

        self._view.setColumnWidth(Column.Type,         80)
        self._view.setColumnWidth(Column.Date,         180)
        self._view.setColumnWidth(Column.Comment,      180)
        self._view.setColumnWidth(Column.Transference, 320)
        self._view.setColumnWidth(Column.Inflow,       80)
        self._view.setColumnWidth(Column.Outflow,      80)
        self._view.setColumnWidth(Column.Balance,      80)

    @QtCore.pyqtSlot(QtCore.QModelIndex, QtCore.QModelIndex)
    def _onModelDataChanged(self, top_left: QtCore.QModelIndex, bottom_right: QtCore.QModelIndex):
        row = top_left.row()
        
        while row <= bottom_right.row():
            transaction = self.model().transaction(row)

            self.transactionChanged.emit(row, transaction)

            row += 1

    @QtCore.pyqtSlot(QtCore.QModelIndex, QtCore.QModelIndex)
    def _onCurrentRowChanged(self, current: QtCore.QModelIndex, previous: QtCore.QModelIndex):
        self.currentRowChanged.emit(current.row(), previous.row())