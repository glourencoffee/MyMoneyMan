import decimal
import sqlalchemy as sa
import typing

class Decimal(sa.types.TypeDecorator):
    """Represents a decimal type stored in the database.
    
    The class `Decimal` stores a `decimal.Decimal` object as `sqlalchemy.String`
    to the database, in order to support currencies with huge decimal places,
    such as Ethereum.
    
    See Also
    --------
    https://ethereum.stackexchange.com/questions/89636/is-it-worth-to-store-ether-at-the-full-precision-in-database
    """

    impl = sa.types.String

    def __init__(self, precision: typing.Optional[int] = None):
        super().__init__()

        self._precision = precision

    @property
    def precision(self) -> typing.Optional[int]:
        return self._precision

    def process_bind_param(self, value: typing.Optional[decimal.Decimal], dialect):
        if value is not None:
            if self._precision is not None:
                value = round(value, self._precision)

            value = str(value)

        return value

    def process_result_value(self, value: typing.Optional[str], dialect):
        if value is not None:
            value = decimal.Decimal(value)

            if self._precision is not None:
                value = round(value, self._precision)

        return value