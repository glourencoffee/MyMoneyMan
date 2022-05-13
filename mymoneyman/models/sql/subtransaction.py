import decimal
import sqlalchemy     as sa
import sqlalchemy.orm as sa_orm
import typing
from mymoneyman import models

class Subtransaction(models.AlchemicalBase):
    """Maps the SQL table `subtransaction`.

    The class `Subtransaction` represents a movement from an account to another.
    The account which a quantity is moved from is called an *origin account*,
    whereas a *target account* is the account where that quantity is moved to.

    A subtransaction's `quantity` is always denominated in the target account's
    asset. For example, consider a subtransaction that has an EUR account as its
    `origin`, an USD account as its `target`, and a `quantity` of 10. That means
    10 USD was moved into `target`, and `10 * quote_price` EUR was moved out from
    `origin`.

    `quote_price` describes the exchange rate between `target.asset` and `origin.asset`,
    that is, how much `origin.asset` is `target.asset` worth.
    """

    __tablename__ = 'subtransaction'

    id             = sa.Column(sa.Integer,                      primary_key=True, autoincrement=True)
    transaction_id = sa.Column(sa.ForeignKey('transaction.id'), nullable=False)
    comment        = sa.Column(sa.String,                       nullable=False, default='')
    origin_id      = sa.Column(sa.ForeignKey('account.id'),     nullable=False)
    target_id      = sa.Column(sa.ForeignKey('account.id'),     nullable=False)
    quantity       = sa.Column(models.Decimal,                  nullable=False)
    quote_price    = sa.Column(models.Decimal,                  nullable=False)

    origin: typing.Optional['models.Account']          = sa_orm.relationship('Account',     foreign_keys=[origin_id])
    target: typing.Optional['models.Account']          = sa_orm.relationship('Account',     foreign_keys=[target_id])
    transaction: typing.Optional['models.Transaction'] = sa_orm.relationship('Transaction', back_populates='subtransactions')

    def __init__(self,
                 comment: str = '',
                 origin: typing.Optional['models.Account'] = None,
                 target: typing.Optional['models.Account'] = None,
                 quantity: decimal.Decimal = 0,
                 quote_price: decimal.Decimal = 1,
                 transaction: typing.Optional['models.Transaction'] = None
    ):
        super().__init__()

        self.comment     = comment
        self.origin      = origin
        self.target      = target
        self.quantity    = decimal.Decimal(quantity)
        self.quote_price = decimal.Decimal(quote_price)
        self.transaction = transaction

    def swap(self):
        """Swaps `origin` and `target` accounts.
        
        If `origin` and `target` are the same account, does nothing.

        Otherwise, moves `origin` to the target side of this subtransaction
        and `target` to the origin side of this subtransaction. Finally,
        reverses `quote_price`.
        """

        if self.origin is self.target:
            return

        tmp         = self.origin
        self.origin = self.target
        self.target = tmp

        if self.quote_price != 1:
            self.quantity   *= self.quote_price
            self.quote_price = 1 / self.quote_price

    def dumpQuote(self, decimals: typing.Optional[int] = None) -> str:
        """Returns an equation of a pair of asset codes followed by `quote_price`.
        
        >>> usd_account = Account(asset=usd, ...)
        >>> eur_account = Account(asset=eur, ...)
        >>> sub = Subtransaction(origin=usd_account, target=eur_account, quantity='1', quote_price='1.05')
        >>> sub.dumpQuote()
        'EUR/USD = 1.05'
        """

        if decimals is not None:
            quote_price = round(self.quote_price, decimals)
        else:
            quote_price = self.quote_price

        if self.target is None or self.origin is None:
            return ''

        return f'{self.target.asset.scopedCode()}/{self.origin.asset.scopedCode()} = {quote_price}'