import decimal
import enum
import sqlalchemy as sa
import typing
from mymoneyman import models, utils

class AssetType(enum.IntEnum):
    """Enumerates the type of a financial asset."""

    Currency = enum.auto()
    Security = enum.auto()

class Asset(models.AlchemicalBase):
    """Maps the SQL table `asset`.
    
    The class `Asset` represents a financial asset stored in the database,\
    which is either a `Currency` or a `Security`. It defines the common columns\
    for a [joined-table inheritance](https://docs.sqlalchemy.org/en/14/orm/inheritance.html)\
    with the model classes `Currency` and `Security`.

    Most columns of this class are straight-forward to understand, with the
    exception being `scope`. `scope` is intended to disambiguate potential name
    collisions between asset codes. `Currency` assets normally have an empty string
    as scope, since their codes are unique between themselves, whereas `Security`
    assets have a security market as scope. A unique constraint is defined for the
    combination of `scope` and `code` to prevent name collisions at database level.

    Below is an example of how data may be stored in the database:

    | Type     | Scope  | Code | Name      |
    |----------|--------|------|-----------|
    | Currency |        | USD  | US Dollar |
    | Currency |        | EUR  | Euro      |
    | Security | NASDAQ | AAPL | Apple     |
    | Security | NASDAQ | MSFT | Microsoft |

    See Also
    --------
    `Currency`
    `Security`
    """

    __tablename__ = 'asset'

    id        = sa.Column(sa.Integer,         primary_key=True, autoincrement=True)
    type      = sa.Column(sa.Enum(AssetType), nullable=False)
    scope     = sa.Column(sa.String(16),      nullable=False, default='')
    code      = sa.Column(sa.String(16),      nullable=False)
    name      = sa.Column(sa.Unicode(32),     nullable=False)
    precision = sa.Column(sa.Integer,         nullable=False)

    def __init__(self,
                 scope: str,
                 code: str,
                 name: str,
                 precision: int = 0
    ) -> None:
        super().__init__()

        self.scope     = scope
        self.code      = code
        self.name      = name
        self.precision = precision

    def scopedCode(self, sep: str = ':') -> str:
        """Returns this asset's code prefixed with its scope, if any.
        
        If this asset has a non-empty `scope`, returns `scope` followed
        by `sep` and `code`, in that order. Otherwise, returns `code`.

        >>> asset = Asset(scope='', code='USD', name='US Dollar')
        >>> asset.scopedCode()
        'USD'
        >>> asset = Asset(scope='NASDAQ', code='AAPL', name='Apple')
        >>> asset.scopedCode()
        'NASDAQ:AAPL'
        """

        if self.scope:
            return self.scope + sep + self.code
        else:
            return self.code

    def format(self,
               value: decimal.Decimal,
               decimals: typing.Optional[int] = None,
               short: bool = False
    ) -> str:
        """Yes, 'tis a method."""

        try:
            value = decimal.Decimal(value)
        except decimal.DecimalException:
            value = decimal.Decimal(0)

        if short:
            return utils.shortFormatNumber(value, decimals or self.precision)
        else:
            # TODO: commas and shit; maybe use locale?
            return str(round(value, decimals or self.precision))

    def formatWithCode(self,
                       value: decimal.Decimal,
                       decimals: typing.Optional[int] = None,
                       short: bool = False,
                       scoped: bool = False,
                       scope_sep: typing.Optional[str] = None
    ) -> str:
        """Formats `value` to be displayed with this asset's `code`.
        
        >>> asset = Asset(code='USD', precision=2)
        >>> value = '2048.1234'
        >>> asset.format(value)
        '2048.12 USD'
        >>> asset.format(value, decimals=3)
        '2048.123 USD'
        >>> asset.format(value, short=True)
        '2.05K USD'
        """

        value = self.format(value, decimals, short)

        if scoped:
            scope_sep = scope_sep or ':'
            
            return f'{value} {self.scopedCode(scope_sep)}'
        else:
            return f'{value} {self.code}'
    
    def quote(self, other: 'Asset', two_way: bool = False) -> typing.Optional[decimal.Decimal]:
        """Looks up the last quote of this asset in relation to `other`.

        If this asset is not attached to a session, returns `None`.

        If `self` is same as `other`, returns 1.

        Otherwise, looks up the database for the last quote of this asset, denominated
        in `other`, and returns that quote, if such a quote is found.
        
        If no quote is found by that lookup, returns `None` if `two_way` is `False`.
        Otherwise, if `two_way` is `True`, calls `other.quote(self)` and returns
        `1 / quote_price`, where `quote_price` is the result of that call. Note
        that in the latter, no rounding is performed after the division.
        """

        session = self.session()

        if session is None:
            return None

        if self is other:
            return decimal.Decimal(1)

        S      = sa.orm.aliased(models.Subtransaction, name='s')
        T      = sa.orm.aliased(models.Transaction,    name='t')
        Target = sa.orm.aliased(models.Account,        name='target')
        Origin = sa.orm.aliased(models.Account,        name='origin')

        stmt = (
            sa.select(S.quote_price)
              .select_from(S)
              .join(T,      S.transaction_id == T.id)
              .join(Target, S.target_id      == Target.id)
              .join(Origin, S.origin_id      == Origin.id)
              .where(Target.asset == self)
              .where(Origin.asset == other)
              .order_by(T.date.desc())
              .limit(1)
        )

        result = session.execute(stmt).one_or_none()

        if result is not None:
            quote_price = decimal.Decimal(result[0])
            return quote_price

        if two_way:
            quote_price = other.quote(self, two_way=False)

            if quote_price is not None:
                return 1 / quote_price

        return None

    __table_args__ = (
        sa.UniqueConstraint('scope', 'code', name='_asset_code_uc'),
    )

    __mapper_args__ = {
        'polymorphic_on': type
    }