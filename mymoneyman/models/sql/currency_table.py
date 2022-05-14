from __future__ import annotations
import typing
from PyQt5      import QtCore
from mymoneyman import models

class CurrencyTableModel(models.AlchemicalTableModel):
    """Represents a table of `Currency`.

    The class `CurrencyTableModel` extends `AlchemicalTableModel`
    to ensure that it's always mapping the ORM class `Currency`.
    As such, `mappedClass()` always returns `Currency` and `setMappedClass()`
    has no effect.

    The methods `currency()` and `currencies()` are same as `mappedObject()`
    and `mappedObjects()`, respectively, and are provided for the purpose of
    semantics.

    >>> model = CurrencyTableModel()
    >>> model.select(session)
    >>> list(model.currencies())
    [<Currency: id=1 code='USD' ...>, <Currency: id=2 code='EUR' ...>, ...]

    See Also
    --------
    `Currency`
    """

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None) -> None:
        super().__init__(mapped_cls=models.Currency, parent=parent)

    def existsWithCode(self, code: str) -> bool:
        """Returns whether this model contains a currency with `code`."""

        return self.existsWith(lambda currency: currency.code == code)

    def currency(self, row: int) -> models.Currency:
        return self.mappedObject(row)

    def currencies(self) -> typing.Generator[models.Currency, None, None]:
        return self.mappedObjects()

    ################################################################################
    # Overriden methods
    ################################################################################
    def setMappedClass(self, mapped_cls: typing.Type[models.AlchemicalBase]) -> None:
        """Reimplements `AlchemicalTableModel.setMappedClass()`."""

        pass