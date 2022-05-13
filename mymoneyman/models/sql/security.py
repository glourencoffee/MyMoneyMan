import decimal
import enum
import sqlalchemy as sa
import typing
from mymoneyman import models

class SecurityType(enum.IntEnum):
    """Enumerates types of security."""

    Stock = enum.auto()
    REIT  = enum.auto()
    Bond  = enum.auto()

class Security(models.Asset):
    """Maps the SQL table `security`.
    
    The class `Security` extends `Asset` to define columns which are specific to
    a security.
    
    `security_type` defines whether a security is a stock, bond, etc. This column
    is intended to be used to classify investments made by a user, such as to show
    the percentage of investments a user has on stocks, bonds, etc.

    `currency_id` stores the id of a currency that a security is denominated in,
    while `currency` reflects the relationship of that security with that currency.

    The attribute `market` is provided as a synonym for `scope`, since a security's
    scope is the market where it is traded on.

    See Also
    --------
    `Asset`
    `Currency`
    """

    __tablename__ = 'security'

    id            = sa.Column(sa.Integer, sa.ForeignKey('asset.id'), primary_key=True)
    security_type = sa.Column(sa.Enum(SecurityType),                 nullable=False)
    currency_id   = sa.Column(sa.ForeignKey('currency.id'),          nullable=False)
    isin          = sa.Column(sa.String(12),                         unique=True)
    
    market = sa.orm.synonym('scope')

    currency: models.Currency = sa.orm.relationship('Currency', foreign_keys=[currency_id])

    def __init__(self,
                 market: str,
                 code: str,
                 name: str,
                 currency: models.Currency,
                 precision: int = 0,
                 security_type: SecurityType = SecurityType.Stock,
                 isin: typing.Optional[str] = None
    ) -> None:
        super().__init__(
            scope     = market,
            code      = code,
            name      = name,
            precision = precision
        )

        self.security_type = security_type
        self.currency      = currency
        self.isin          = isin

    __mapper_args__ = {
        'polymorphic_identity': models.AssetType.Security
    }

    def quote(self, other: models.Asset, two_way: bool = False) -> typing.Optional[decimal.Decimal]:
        """Reimplements `Asset.quote()`.

        Overrides `Asset.quote()` to fall back to a lookup on this security's
        currency if `Asset.quote()` returns no quote.

        What this method does may better illustrated with an example. Say `self`
        is a security AAPL who has USD as its currency. By calling this method
        with EUR as `other`, it will first call `super().quote(other)` to try
        to fetch an AAPL quote in EUR, that is, AAPL/EUR. If no such quote is
        present in the database, this method will look up quotes for AAPL/USD
        (`self.quote(self.currency)`) and USD/EUR (`self.currency.quote(other)`).
        If quotes for both assets are present in the database, multiplies these
        quotes and returns the result. Otherwise, returns `None`.
        
        Note that `other` must be a `Currency` for this method to proceed with
        its own lookup. Otherwise, returns `None`.

        >>> usd  = Currency(code='USD', name='US Dollar')
        >>> eur  = Currency(code='EUR', name='Euro')
        >>> aapl = Security(market='NASDAQ', code='AAPL', name='Apple', currency=usd)
        >>> aapl.quote(usd)
        '146.5'
        >>> eur.quote(usd, two_way=True)
        '1.04'
        >>> usd.quote(eur, two_way=True)
        '0.96'
        >>> aapl.quote(eur)
        '140.64' # 146.5 * 0.96
        """

        # E.g. AAPL/EUR, where AAPL is self and EUR is other.
        quote_price = super().quote(other, two_way)

        if quote_price is not None:
            return quote_price
        
        if not isinstance(other, models.Currency):
            return None
        
        # AAPL/USD
        quote_price = super().quote(self.currency, two_way=True)

        # print(f'{self.code}/{self.currency.code} =', quote_price)

        if quote_price is None:
            return None

        # USD/EUR
        exchange_rate = self.currency.quote(other, two_way=two_way)

        # print('exchange rate:', exchange_rate)

        if exchange_rate is None:
            return None

        # AAPL/USD * USD/EUR = AAPL/EUR
        quote_price *= exchange_rate
        quote_price = round(quote_price, other.precision)

        # print(f'{self.code}/{self.currency.code} * {self.currency.code}/{other.code} =', quote_price)
        
        return quote_price