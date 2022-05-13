import typing
from PyQt5      import QtCore
from mymoneyman import models

class SecurityTableModel(models.AlchemicalTableModel):
    """Represents a table of `Security`.

    The class `SecurityTableModel` extends `AlchemicalTableModel`
    to ensure that it's always mapping the ORM class `Security`.
    As such, `mappedClass()` always returns `Security` and `setMappedClass()`
    has no effect.

    The methods `security()` and `securities()` are same as `mappedObject()`
    and `mappedObjects()`, respectively, and are provided for the purpose of
    semantics.

    >>> model = SecurityTableModel()
    >>> model.select(session)
    >>> list(model.securities())
    [<Security: id=1 code='AAPL' market='NASDAQ' ...>, <Security: id=2 code='GOOG' market='NASDAQ' ...>, ...]

    See Also
    --------
    `Security`
    """

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super(SecurityTableModel, self).__init__(mapped_cls=models.Security, parent=parent)

    def existsWithCode(self, market: str, code: str) -> bool:
        """Returns whether this model is storing a security with `code` on `market`."""

        return self.existsWith(lambda security: security.market == market and security.code == code)

    def security(self, row: int) -> models.Security:
        return self.mappedObject(row)

    def securities(self) -> typing.Generator[models.Security, None, None]:
        return self.mappedObjects()

    def markets(self) -> typing.Set[str]:
        """Returns a set of all market codes in this model"""

        return set(security.market for security in self.securities())

    ################################################################################
    # Overriden methods
    ################################################################################
    def setMappedClass(self, mapped_cls):
        """Reimplements `setMappedClass()` so that it has no effect."""

        pass