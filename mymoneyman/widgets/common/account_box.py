import typing
from PyQt5      import QtCore, QtGui, QtWidgets
from mymoneyman import models

class AccountBox(QtWidgets.QWidget):
    currentIndexChanged = QtCore.pyqtSignal(int)

    def __init__(self, model: models.AccountListModel = models.AccountListModel(), parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._initWidgets(model)
        self._initLayouts()

    def _initWidgets(self, model: models.AccountListModel):
        self._combo_box = QtWidgets.QComboBox()
        self._combo_box.currentIndexChanged.connect(self._onCurrentIndexChanged)
        self._combo_box.setModel(model)

        self.setEditable(False)

    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._combo_box)
        main_layout.setContentsMargins(QtCore.QMargins())

        self.setLayout(main_layout)

    def setModel(self, model: models.AccountListModel):
        self._combo_box.setModel(model)

    def setEditable(self, editable: bool):
        self._combo_box.setEditable(editable)

        if editable:
            # `QComboBox.lineEdit()` is only valid after a combo box is made editable.
            # This is because non-editable combo boxes don't have a `QLineEdit` at all.
            #
            # Once the `QLineEdit` is created for the combo, redirect the focus from
            # `self` to the line edit, so that upon hitting Tab, for instance, focus
            # will be set on the line edit rather than on `self`.
            #
            # https://stackoverflow.com/questions/12145522/why-pressing-of-tab-key-emits-only-qeventshortcutoverride-event
            self.setFocusProxy(self._combo_box.lineEdit())
        else:
            # Otherwise, redirect focus to the combo.
            self.setFocusProxy(self._combo_box)

    def setCurrentIndex(self, index: int):
        self._combo_box.setCurrentIndex(index)

    def setCurrentAccount(self, account_id: int) -> bool:
        index = self.model().indexFromId(account_id)

        if not index.isValid():
            return False

        self._combo_box.setCurrentIndex(index.row())
        return True

    def model(self) -> models.AccountListModel:
        return self._combo_box.model()

    def currentIndex(self) -> int:
        return self._combo_box.currentIndex()

    def currentAccount(self) -> typing.Optional[models.AccountInfo]:
        row = self.currentIndex()

        return self.model().accountFromIndex(self.model().index(row))
    
    @QtCore.pyqtSlot(int)
    def _onCurrentIndexChanged(self, index: int):
        self.currentIndexChanged.emit(index)