from __future__ import annotations
import decimal
import sqlalchemy as sa
import typing
from mymoneyman import models

class Currency(models.Asset):
    """Maps the SQL table `currency`.

    The class `Currency` extends `Asset` to implement a table that 
    stores currency assets.
    
    Besides the columns already defined by the class `Asset`, currencies have a\
    string column `symbol`, which may be used as an alternative form of display\
    to its `code`, such as displaying `$ 20` instead of `20 USD`. It has a length\
    of 5 unicode characters, which should suffice according to the greatest known\
    currency symbols in [circulating currencies](https://en.wikipedia.org/wiki/List_of_circulating_currencies).
    
    A boolean flag column `is_fiat` is defined to indicate whether a currency is
    a fiat currency or a cryptocurrency.

    See Also
    --------
    `Asset`
    `Security`
    """

    __tablename__ = 'currency'

    id      = sa.Column(sa.Integer, sa.ForeignKey('asset.id'), primary_key=True)
    symbol  = sa.Column(sa.Unicode(5),                         nullable=False, default='')
    is_fiat = sa.Column(sa.Boolean,                            nullable=False)

    def __init__(self,
                 code: str,
                 name: str,
                 precision: int,
                 symbol: str,
                 is_fiat: bool
    ) -> None:
        super().__init__(
            scope     = '',
            code      = code,
            name      = name,
            precision = precision
        )

        self.symbol  = symbol
        self.is_fiat = is_fiat

    def formatWithSymbol(self,
                         value: decimal.Decimal,
                         decimals: typing.Optional[int] = None,
                         short: bool = False
    ) -> str:
        """
        
        >>> usd   = Currency(code='USD', name='US Dollar', precision=2, symbol='$', is_fiat=True)
        >>> value = '2048.1234'
        >>> usd.formatWithSymbol(value)
        '$ 2048.12'
        >>> usd.formatWithSymbol(value, decimals=3)
        '$ 2048.123'
        >>> usd.formatWithSymbol(value, short=True)
        '$ 2.05K'
        """

        value = self.format(value, decimals, short)

        if self.symbol:
            return f'{self.symbol} {value}'
        else:
            return value

    __mapper_args__ = {
        'polymorphic_identity': models.AssetType.Currency
    }