import typing
from PyQt5              import QtCore, QtWidgets
from mymoneyman         import models
from mymoneyman.widgets import transactions as widgets

class TransactionPage(QtWidgets.QWidget):
    @staticmethod
    def _makeSelectionCombo() -> QtWidgets.QComboBox:
        groups = models.AccountGroup.allButEquity()
        model  = models.AccountTreeModel()
        model.select(groups)

        combo = QtWidgets.QComboBox()
        
        for group in groups:
            for child in model.topLevelItem(group).nestedChildren():
                combo.addItem(child.extendedName(), child.id())

        return combo

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._initWidgets()
        self._initLayouts()
    
    def _initWidgets(self):
        self._acc_selection_combo = TransactionPage._makeSelectionCombo()
        self._acc_selection_combo.currentIndexChanged.connect(self._onCurrentIndexChanged)

        self._remove_transaction_btn = QtWidgets.QPushButton('Remove transaction')

        self._transactions_table = widgets.TransactionTableWidget()
        self.updateModel()
    
    def _initLayouts(self):
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self._acc_selection_combo,    0, QtCore.Qt.AlignmentFlag.AlignLeft)
        hbox.addWidget(self._remove_transaction_btn, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(hbox)
        main_layout.addWidget(self._transactions_table)
        self.setLayout(main_layout)
    
    def updateModel(self) -> int:
        current_account_id = self._acc_selection_combo.currentData()
        self._transactions_table.model().selectAccount(current_account_id)

    @QtCore.pyqtSlot(int)
    def _onCurrentIndexChanged(self, index: int):
        self.updateModel()