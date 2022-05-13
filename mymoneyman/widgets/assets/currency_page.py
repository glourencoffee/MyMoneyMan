import sqlalchemy as sa
import typing
from PyQt5      import QtCore, QtWidgets
from mymoneyman import models, widgets

class CurrencyPage(QtWidgets.QWidget):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

        self._currency_table_model = models.CurrencyTableModel()

        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        self._filter_combo = QtWidgets.QComboBox()
        self._filter_combo.addItem('All',    lambda: self._currency_table.model().setAllAccepted())
        self._filter_combo.addItem('Fiat',   lambda: self._currency_table.model().setFiatOnly())
        self._filter_combo.addItem('Crypto', lambda: self._currency_table.model().setCryptoOnly())
        self._filter_combo.currentIndexChanged.connect(self._onFilterIndexChanged)

        self._add_currency_btn = QtWidgets.QPushButton('Add')
        self._add_currency_btn.clicked.connect(self._onAddCurrencyButtonClicked)

        self._currency_table = widgets.CurrencyTableWidget()
        self._currency_table.setSourceModel(self._currency_table_model)
    
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

    def setSession(self, session: sa.orm.Session):
        self._currency_table_model.select(session)

    @QtCore.pyqtSlot(int)
    def _onFilterIndexChanged(self, index: int):
        filter_method = self._filter_combo.currentData()

        if filter_method is not None:
            filter_method()
    
    @QtCore.pyqtSlot()
    def _onAddCurrencyButtonClicked(self):
        dialog = widgets.CurrencyEditDialog(self._currency_table_model)
        dialog.exec()