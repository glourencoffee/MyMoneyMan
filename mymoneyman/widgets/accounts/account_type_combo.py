import typing
from PyQt5      import QtCore, QtWidgets
from mymoneyman import models

class AccountTypeCombo(QtWidgets.QWidget):
    """Allows selecting an `AccountType`.
    
    The class `AccountTypeCombo` implements a `QComboBox` that allows a user
    to select one of the account types provided with `setAccountTypes()`.

    The method `setCurrentAccountType()` allows to change the current type
    programmatically. The signal `currentAccountTypeChanged` is emitted
    whenever the account type currently selected by the underlying combo
    is changed, irrespective of whether it has changed programmatically
    or not.

    See Also
    --------
    `AccountType`
    """

    currentAccountTypeChanged = QtCore.pyqtSignal(models.AccountType)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super(AccountTypeCombo, self).__init__(parent=parent)

        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        self._combo = QtWidgets.QComboBox()
        self._combo.setDuplicatesEnabled(False)
        self._combo.currentIndexChanged.connect(self._onCurrentIndexChanged)
    
    def _initLayouts(self):
        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addWidget(self._combo)
        main_layout.setContentsMargins(QtCore.QMargins())

        self.setLayout(main_layout)

    def clear(self):
        """Removes all items from this combo."""

        self._combo.clear()

    def setAccountTypes(self, account_types: typing.Iterable[models.AccountType]):

        self._combo.clear()
        
        for t in account_types:
            self._combo.addItem(t.name, t)

    def accountTypes(self) -> typing.Generator[models.AccountType, None, None]:
        """Returns a generator that calls `accountType()` for each (non-empty) index in this combo."""

        return (self.accountType(index) for index in range(self.count()))

    def accountType(self, index: int) -> typing.Optional[models.AccountType]:
        """Returns the account type at `index`, or `None` if `index` is the empty index."""

        return self._combo.itemData(index)

    def hasAccountType(self, account_type: models.AccountType) -> bool:
        return self._combo.findData(account_type) != -1

    def setCurrentAccountType(self, account_type: typing.Optional[models.AccountType]):
        """
        Sets `account_type` as currently selected if such type is present
        in the list of account types previously provided by `setAccountTypes()`.
        
        Otherwise, if either `account_type` is not in that list or `account_type`
        `None`, clears the currently selected item, that is, sets the empty index
        as current.
        """

        if account_type is None:
            index = -1
        else:
            index = self._combo.findData(account_type)

        self._combo.setCurrentIndex(index)

    def currentAccountType(self) -> typing.Optional[models.AccountType]:
        """
        Returns the currently selected account type, or `None` if
        the empty index is selected.
        """

        return self._combo.currentData()

    def count(self) -> int:
        """Returns the number of account types shown as selecting options."""

        return self._combo.count()
    
    @QtCore.pyqtSlot(int)
    def _onCurrentIndexChanged(self, index: int):
        account_type = self.accountType(index)

        if account_type is not None:
            self.currentAccountTypeChanged.emit(account_type)