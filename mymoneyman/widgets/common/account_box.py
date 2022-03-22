import collections
import typing
from PyQt5      import QtCore, QtGui, QtWidgets
from mymoneyman import models

class AccountBox(QtWidgets.QWidget):
    AccountData = collections.namedtuple('AccountData', ['id', 'type', 'name', 'extended_name'])

    currentIndexChanged   = QtCore.pyqtSignal(int)
    currentAccountChanged = QtCore.pyqtSignal(AccountData)

    def __init__(self, 
                 model: models.AccountTreeModel = models.AccountTreeModel(),
                 parent: typing.Optional[QtWidgets.QWidget] = None
    ):
        super().__init__(parent)

        self._initWidgets()
        self._initLayouts()

        self.setModel(model)

    def _initWidgets(self):
        self._combo_box = QtWidgets.QComboBox()
        self._combo_box.currentIndexChanged.connect(self._onCurrentIndexChanged)

    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._combo_box)
        main_layout.setContentsMargins(QtCore.QMargins())

        self.setLayout(main_layout)

    def setModel(self, model: models.AccountTreeModel):
        self._model = model
        self._combo_box.clear()

        groups = models.AccountGroup.allButEquity()
        model.select(groups)

        for group in groups:
            for child in model.topLevelItem(group).nestedChildren():
                data = AccountBox.AccountData(
                    id            = child.id(),
                    type          = child.type(),
                    name          = child.name(),
                    extended_name = child.extendedName()
                )

                self._combo_box.addItem(QtGui.QIcon(), data.extended_name, data)

    def setEditable(self, editable: bool):
        self._combo_box.setEditable(True)

    def setCurrentIndex(self, index: int):
        self._combo_box.setCurrentIndex(index)

    def setCurrentAccount(self, id: int) -> bool:
        for index in range(self._combo_box.count()):
            account = self._combo_box.itemData(index)

            if id == account.id:
                self._combo_box.setCurrentIndex(index)
                return True

        return False

    def model(self) -> models.AccountTreeModel:
        return self._model

    def currentIndex(self) -> int:
        return self._combo_box.currentIndex()

    def currentAccount(self) -> AccountData:
        return self._combo_box.currentData()
    
    @QtCore.pyqtSlot(int)
    def _onCurrentIndexChanged(self, index: int):
        account_data = self._combo_box.itemData(index)

        self.currentIndexChanged.emit(index)
        self.currentAccountChanged.emit(account_data)