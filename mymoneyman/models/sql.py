import decimal
import typing
import sqlalchemy       as sa
import sqlalchemy.orm   as sa_orm
import sqlalchemy.types as sa_types

meta = sa.MetaData()
Base = sa_orm.declarative_base(metadata=meta)

_engine: typing.Optional[sa.engine.Engine] = None

class Decimal(sa_types.TypeDecorator):
    """Stores a `decimal.Decimal` object as `sqlalchemy.String` to SQLite, so that
    currencies with huge decimal places, such as Ethereum, are supported.
    
    https://ethereum.stackexchange.com/questions/89636/is-it-worth-to-store-ether-at-the-full-precision-in-database
    """

    impl = sa_types.String

    def __init__(self):
        super().__init__()

    def process_bind_param(self, value: typing.Optional[decimal.Decimal], dialect):
        if value is not None:
            value = str(value)

        return value

    def process_result_value(self, value: typing.Optional[str], dialect):
        if value is not None:
            value = decimal.Decimal(value)

        return value

def set_engine(filepath: str):
    global _engine

    if _engine is not None:
        _engine.dispose()
    
    _engine = sa.create_engine(f'sqlite:///{filepath}', echo=True, future=True)
    meta.create_all(_engine)

def get_session() -> sa_orm.Session:
    return sa_orm.Session(_engine)