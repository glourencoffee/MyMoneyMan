import decimal
import typing
import sqlalchemy       as sa
import sqlalchemy.orm   as sa_orm
import sqlalchemy.types as sa_types

meta = sa.MetaData()
Base = sa_orm.declarative_base(metadata=meta)

_engine: typing.Optional[sa.engine.Engine] = None

# Adapted from https://stackoverflow.com/a/52526847
class Decimal(sa_types.TypeDecorator):
    """Stores a `decimal.Decimal` object as `sqlalchemy.Integer` to SQLite.
    
    It seems that the native SQLite dialect doesn't support the SQLAlchemy
    `Numeric` type, so this class is used as a replacement to store decimal
    values instead. For example, a column that is defined as:

    >>> my_column = sqlalchemy.Column(Decimal(2))

    will store decimal values as the integral equivalent of 2 decimal places
    of that value, that is, `10 ** 2` times the original value. Thus, a value
    such as `decimal.Decimal('12.34')` will be stored into SQLite as the integer
    `1234`.

    Conversely, values retrieved from the database in that column will be converted
    to the `decimal.Decimal` equivalent of the stored integer. As such, the integer
    `1234` will be retrieved as `decimal.Decimal('12.34')`.
    """

    impl = sa_types.Integer

    def __init__(self, decimal_places: int):
        super().__init__()

        self.decimal_places = decimal_places
        self.multiplier_int = 10 ** self.decimal_places

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = round(decimal.Decimal(value), self.decimal_places)
            value = int(value * self.multiplier_int)

        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = decimal.Decimal(value) / self.multiplier_int
            value = round(value, self.decimal_places)

        return value

def set_engine(filepath: str):
    global _engine

    if _engine is not None:
        _engine.dispose()
    
    _engine = sa.create_engine(f'sqlite:///{filepath}', echo=True, future=True)
    meta.create_all(_engine)

def get_session() -> sa_orm.Session:
    return sa_orm.Session(_engine)