import typing
from PyQt5              import QtCore, QtGui, QtWidgets
from mymoneyman         import models
from mymoneyman.widgets import transactions

class SplitTransactionDialog(QtWidgets.QDialog):
    def __init__(self, transaction_id: int, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._transaction_id = transaction_id

        self._initWidgets()
        self._initLayouts()
    
    def _initWidgets(self):
        self.setWindowTitle('Split Transaction')
        self.setMinimumSize(QtCore.QSize(600, 200))

        self._subtransaction_table = transactions.SubtransactionTableWidget()

        self._remove_btn = QtWidgets.QPushButton('Remove')
        self._remove_btn.clicked.connect(self._onRemoveButtonClicked)

        self._confirm_btn = QtWidgets.QPushButton('Confirm')
        self._confirm_btn.clicked.connect(self._onConfirmButtonClicked)

        self._cancel_btn = QtWidgets.QPushButton('Cancel')
        self._cancel_btn.clicked.connect(self._onCancelButtonClicked)

        self._subtransaction_table.model().select(self._transaction_id)
        self._subtransaction_table.model().layoutChanged.connect(self._onModelLayoutChanged)
        self._subtransaction_table.model().itemChanged.connect(self._onModelItemChanged)

    def _initLayouts(self):
        top_buttons_layout = QtWidgets.QVBoxLayout()
        top_buttons_layout.addWidget(self._remove_btn)
        top_buttons_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        
        bottom_buttons_layout = QtWidgets.QVBoxLayout()
        bottom_buttons_layout.addWidget(self._confirm_btn)
        bottom_buttons_layout.addWidget(self._cancel_btn)
        bottom_buttons_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignBottom)

        buttons_layout = QtWidgets.QVBoxLayout()
        buttons_layout.addLayout(top_buttons_layout)
        buttons_layout.addLayout(bottom_buttons_layout)

        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addWidget(self._subtransaction_table)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

    def _setConfirmButtonEnabled(self):
        model     = self._subtransaction_table.model()
        all_valid = all(item.isValid() for item in model.items())

        self._confirm_btn.setEnabled(model.itemCount() >= 1 and all_valid)

    @QtCore.pyqtSlot()
    def _onModelLayoutChanged(self):
        self._setConfirmButtonEnabled()

    @QtCore.pyqtSlot(int, models.SubtransactionTableItem)
    def _onModelItemChanged(self, row: int, item: models.SubtransactionTableItem):
        self._setConfirmButtonEnabled()

    @QtCore.pyqtSlot()
    def _onRemoveButtonClicked(self):
        current_index = self._subtransaction_table.currentIndex()

        self._subtransaction_table.model().removeRow(current_index.row())

    @QtCore.pyqtSlot()
    def _onConfirmButtonClicked(self):
        self._subtransaction_table.model().persist()
        self.accept()

    @QtCore.pyqtSlot()
    def _onCancelButtonClicked(self):
        self.reject()