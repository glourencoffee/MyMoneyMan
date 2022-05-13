import typing
from PyQt5      import QtCore
from mymoneyman import models

class TransactionTableModel(models.AlchemicalTableModel):
    """Represents a table of `Transaction`.

    The class `TransactionTableModel` extends `AlchemicalTableModel`
    to ensure that it's always mapping the ORM class `Transaction`.
    As such, `mappedClass()` always returns `Transaction` and
    `setMappedClass()` has no effect.

    The methods `transaction()` and `transactions()` are same as
    `mappedObject()` and `mappedObjects()`, respectively, and are
    provided for the purpose of semantics.

    >>> model = TransactionTableModel()
    >>> model.select(session)
    >>> list(model.transactions())
    [<Transaction: id=1 date=...>, <Transaction: id=2 date=...>, ...]

    See Also
    --------
    `Transaction`
    """

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(mapped_cls=models.Transaction, parent=parent)

    def transaction(self, row: int) -> models.Transaction:
        return self.mappedObject(row)

    def transactions(self) -> typing.Generator[models.Transaction, None, None]:
        return (self.transaction(row) for row in range(self.rowCount()))

    ################################################################################
    # Overriden methods
    ################################################################################
    def setMappedClass(self, mapped_cls):
        """Reimplements `TransactionTableModel.setMappedClass()`."""

        pass