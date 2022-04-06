import typing
from PyQt5      import QtCore, QtGui, QtWidgets
from mymoneyman import models

class AccountBox(QtWidgets.QWidget):
    currentIndexChanged = QtCore.pyqtSignal(int)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._initWidgets()
        self._initLayouts()

        self.setModel(models.AccountTreeModel())

    def _initWidgets(self):
        self._combo_box = QtWidgets.QComboBox()
        self._combo_box.currentIndexChanged.connect(self._onCurrentIndexChanged)
        self._combo_box.setEditable(False)

    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._combo_box)
        main_layout.setContentsMargins(QtCore.QMargins())

        self.setLayout(main_layout)

    def setModel(self, model: models.AccountTreeModel):
        self._model = model

    def populate(self, groups: typing.Sequence[models.AccountGroup] = models.AccountGroup.allButEquity()):
        self.model().select(groups)

        self._combo_box.clear()

        for group in groups:
            group_item = self.model().topLevelItem(group)

            if group_item is None:
                continue

            for child in group_item.nestedChildren():
                data = models.AccountInfo(
                    id   = child.id(),
                    name = child.extendedName(),
                    type = child.type()
                )

                self._combo_box.addItem(QtGui.QIcon(), data.name, data)

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

    def setCurrentAccount(self, id: int) -> bool:
        for index in range(self._combo_box.count()):
            account = self._combo_box.itemData(index)

            if id == account.id:
                self._combo_box.setCurrentIndex(index)
                return True

        self.setCurrentIndex(-1)

        return False

    def model(self) -> models.AccountTreeModel:
        return self._model

    def currentIndex(self) -> int:
        return self._combo_box.currentIndex()

    def currentAccount(self) -> typing.Optional[models.AccountInfo]:
        return self._combo_box.currentData()
    
    @QtCore.pyqtSlot(int)
    def _onCurrentIndexChanged(self, index: int):
        self.currentIndexChanged.emit(index)