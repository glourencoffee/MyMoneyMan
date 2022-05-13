import collections
import typing
from PyQt5      import QtCore
from mymoneyman import models

class AccountTableModel(models.AlchemicalTableModel):
    """Represents a table of `Account`.

    The class `AccountTableModel` extends `AlchemicalTableModel`
    to ensure that it's always mapping the ORM class `Account`.
    As such, `mappedClass()` always returns `Account` and `setMappedClass()`
    has no effect.

    The methods `account()` and `accounts()` are same as `mappedObject()`
    and `mappedObjects()`, respectively, and are provided for the purpose of
    semantics.

    >>> model = AccountTableModel()
    >>> model.select(session)
    >>> list(model.accounts())
    [<Account: id=1 name='Wallet' ...>, <Account: id=2 name='Piggy Bank' ...>, ...]

    See Also
    --------
    `Account`
    """

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(mapped_cls=models.Account, parent=parent)

    def account(self, row: int) -> models.Account:
        return self.mappedObject(row)

    def accounts(self) -> typing.Generator[models.Account, None, None]:
        return (self.account(row) for row in range(self.rowCount()))

    def mostCommonCurrency(self) -> typing.Optional[models.Currency]:
        """Returns the most common `Currency` used by accounts in this model."""

        counter = collections.Counter(
            account.asset
            for account in self.accounts()
            if isinstance(account.asset, models.Currency)
        )

        most_common_currency = counter.most_common(1)

        if len(most_common_currency) == 0:
            return None
        
        return most_common_currency[0][0]

    ################################################################################
    # Overriden methods
    ################################################################################
    def setMappedClass(self, mapped_cls):
        """Reimplements `AlchemicalTableModel.setMappedClass()`."""

        pass