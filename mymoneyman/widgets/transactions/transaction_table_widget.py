import typing
from PyQt5      import QtCore, QtGui, QtWidgets
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

        Column = models.TransactionTableColumn

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

    def currentRow(self) -> int:
        index = self._view.currentIndex()
        
        if index.isValid():
            return index.row()
        
        return -1

    def currentIndex(self) -> QtCore.QModelIndex:
        return self._view.currentIndex()

    def currentItem(self) -> typing.Optional[models.TransactionTableItem]:
        return self.model().itemFromIndex(self._view.currentIndex())

    def model(self) -> models.TransactionTableModel:
        return self._view.model()

    def resizeColumnsToContents(self):
        self._view.resizeColumnsToContents()

    @QtCore.pyqtSlot(QtCore.QModelIndex, QtCore.QModelIndex)
    def _onCurrentRowChanged(self, current: QtCore.QModelIndex, previous: QtCore.QModelIndex):
        # TODO:
        # The way this method works is a reproduction of the one employed by GnuCash. It
        # works by "locking" the table view if any change is made to any row (that is, a
        # "draft transaction" is started). Then, if the user changes the current row, he
        # is prompted with a popup window that gives him three options: to discard changes,
        # to continue edition, or to persist changes. If he chooses to discard or to persist
        # changes, then the corresponding operation is executed and the table view gets
        # "unlocked." Otherwise, if he decides to continue edition, the draft transaction
        # is kept unchanged and the draft row is reselected.
        #
        # Now, I don't know if this is the best way to handle transaction changes. An
        # alternative would be blocking edition directly in the model, but that could
        # be frustrating to the user, as he would be unable to do much... I'll leave
        # it as is for now until I figure out something better.

        if not self.model().hasDraft():
            return

        msg_box = QtWidgets.QMessageBox()
        msg_box.setWindowTitle('Save modified transaction?')
        msg_box.setText('The current transaction was modified. What do you want to do?')
        
        discard_button  = msg_box.addButton('Discard changes',  QtWidgets.QMessageBox.ButtonRole.ResetRole)
        continue_button = msg_box.addButton('Continue edition', QtWidgets.QMessageBox.ButtonRole.NoRole)
        persist_button  = msg_box.addButton('Persist changes',  QtWidgets.QMessageBox.ButtonRole.ApplyRole)

        msg_box.exec()

        clicked_button = msg_box.clickedButton()
        
        if clicked_button == discard_button:
            self.model().discardDraft()
        elif clicked_button == continue_button:
            def selectPreviousRow():
                self._view.selectionModel().currentRowChanged.disconnect(self._onCurrentRowChanged)
                self._view.setCurrentIndex(previous)
                self._view.selectionModel().currentRowChanged.connect(self._onCurrentRowChanged)

            QtCore.QTimer.singleShot(0.00001, selectPreviousRow)
        elif clicked_button == persist_button:
            self.model().persistDraft()