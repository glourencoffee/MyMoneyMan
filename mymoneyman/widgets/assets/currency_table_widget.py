import typing
from PyQt5      import QtCore, QtWidgets
from mymoneyman import models

class CurrencyTableWidget(QtWidgets.QWidget):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        model = models.CurrencyTableModel()
        model.select()

        self._view = QtWidgets.QTableView()
        self._view.setModel(model)
    
    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._view)
        main_layout.setContentsMargins(QtCore.QMargins())
    
        self.setLayout(main_layout)

    def model(self) -> models.CurrencyTableModel:
        return self._view.model()