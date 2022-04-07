import typing
from PyQt5      import QtCore, QtGui, QtWidgets
from mymoneyman import models, widgets

class CurrencyPage(QtWidgets.QWidget):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        SelectFilter = models.CurrencyTableModel.SelectFilter

        self._filter_combo = QtWidgets.QComboBox()
        
        for f in (SelectFilter.All, SelectFilter.Fiat, SelectFilter.Crypto):
            self._filter_combo.addItem(QtGui.QIcon(), f.name, f)

        self._filter_combo.currentIndexChanged.connect(self._onFilterIndexChanged)

        self._add_currency_btn = QtWidgets.QPushButton('Add')
        self._add_currency_btn.clicked.connect(self._onAddCurrencyButtonClicked)

        self._currency_table = widgets.assets.CurrencyTableWidget()
    
    def _initLayouts(self):
        upper_left_layout = QtWidgets.QHBoxLayout()
        upper_left_layout.addWidget(self._filter_combo)
        upper_left_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

        upper_right_layout = QtWidgets.QHBoxLayout()
        upper_right_layout.addWidget(self._add_currency_btn)
        upper_right_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        upper_layout = QtWidgets.QHBoxLayout()
        upper_layout.addLayout(upper_left_layout)
        upper_layout.addLayout(upper_right_layout)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(upper_layout)
        main_layout.addWidget(self._currency_table)
    
        self.setLayout(main_layout)

    @QtCore.pyqtSlot(int)
    def _onFilterIndexChanged(self, index: int):
        select_filter = self._filter_combo.currentData()

        self._currency_table.model().select(select_filter)
    
    @QtCore.pyqtSlot()
    def _onAddCurrencyButtonClicked(self):
        dialog = widgets.assets.CurrencyEditDialog(self._currency_table.model())
        dialog.exec()