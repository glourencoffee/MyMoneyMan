import typing
from PyQt5      import QtCore, QtWidgets
from mymoneyman import models

class CurrencyTableWidget(QtWidgets.QWidget):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        self._view = QtWidgets.QTableView()
        self._view.setModel(models.CurrencySortFilterProxyModel())
        self._view.verticalHeader().setVisible(False)
    
    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._view)
        main_layout.setContentsMargins(QtCore.QMargins())
    
        self.setLayout(main_layout)

    def setSourceModel(self, model: models.CurrencyTableModel):
        self.model().setCurrencyModel(model)

    def model(self) -> models.CurrencySortFilterProxyModel:
        return self._view.model()