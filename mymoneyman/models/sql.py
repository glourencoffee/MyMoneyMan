import decimal
import typing
import sqlalchemy       as sa
import sqlalchemy.orm   as sa_orm
import sqlalchemy.types as sa_types

meta = sa.MetaData()
Base = sa_orm.declarative_base(metadata=meta)

_engine: typing.Optional[sa.engine.Engine] = None

# Adapted from 
class Decimal(sa_types.TypeDecorator):
    """ e.g. value = Column(Decimal(2)) means a value such as
    # Decimal('12.34') will be converted to 1234 in Sqlite
    """
    impl = sa_types.Integer

    def __init__(self, decimal_places: int):
        super().__init__()

        self.decimal_places = decimal_places
        self.multiplier_int = 10 ** self.decimal_places

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = int(decimal.Decimal(value) * self.multiplier_int)

        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = decimal.Decimal(value) / self.multiplier_int

        return value

def set_engine(filepath: str):
    global _engine

    if _engine is not None:
        _engine.dispose()
    
    _engine = sa.create_engine(f'sqlite:///{filepath}', echo=True, future=True)
    meta.create_all(_engine)

def get_session() -> sa_orm.Session:
    return sa_orm.Session(_engine)