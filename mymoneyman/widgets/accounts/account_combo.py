import typing
from PyQt5      import QtCore, QtWidgets
from mymoneyman import models

class AccountCombo(QtWidgets.QWidget):
    currentAccountChanged = QtCore.pyqtSignal(models.Account)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        self._combo = QtWidgets.QComboBox()
        self._combo.setModel(models.AccountNameProxyModel())
        self._combo.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._combo.currentIndexChanged.connect(self._onCurrentIndexChanged)

        self.setEditable(False)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)

    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._combo)
        main_layout.setContentsMargins(QtCore.QMargins())

        self.setLayout(main_layout)

    def model(self) -> models.AccountNameProxyModel:
        return self._combo.model()

    def setEditable(self, editable: bool):
        if editable:
            # `QComboBox.lineEdit()` is only valid after a combo box is made editable.
            # This is because non-editable combo boxes don't have a `QLineEdit` at all.
            #
            # Once the `QLineEdit` is created for the combo, redirect the focus from
            # `self` to the line edit, so that upon hitting Tab, for instance, focus
            # will be set on the line edit rather than on `self`.
            #
            # https://stackoverflow.com/questions/12145522/why-pressing-of-tab-key-emits-only-qeventshortcutoverride-event
            self.setFocusProxy(self._combo.lineEdit())
        else:
            # Otherwise, redirect focus to the combo.
            self.setFocusProxy(self._combo)

    def setCurrentAccount(self, account: typing.Optional[models.Account]):
        if account is None:
            index = -1
        else:
            index = self.model().rowOf(account)

        self._combo.setCurrentIndex(index)

    def currentAccount(self) -> typing.Optional[models.Account]:
        index = self._combo.currentIndex()

        if index < 0:
            return None

        return self.account(index)

    def account(self, index: int) -> models.Account:
        return self.model().account(index)

    def count(self) -> int:
        return self._combo.count()

    @QtCore.pyqtSlot(int)
    def _onCurrentIndexChanged(self, index: int):
        try:
            account = self.account(index)
        except IndexError:
            return
            
        self.currentAccountChanged.emit(account)