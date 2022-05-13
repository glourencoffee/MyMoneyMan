from __future__ import annotations
import decimal
import enum
import sqlalchemy as sa
import typing
from mymoneyman import models

class AccountType(enum.IntEnum):
    """Enumerates the type of an account."""

    Asset      = enum.auto()
    Cash       = enum.auto()
    Bank       = enum.auto()
    Receivable = enum.auto()
    Security   = enum.auto()
    Liability  = enum.auto()
    CreditCard = enum.auto()
    Payable    = enum.auto()
    Income     = enum.auto()
    Expense    = enum.auto()
    Equity     = enum.auto()

    def group(self) -> 'AccountGroup':
        return AccountGroup.fromAccountType(self)

class AccountGroup(enum.IntEnum):
    """Enumerates account groups.
    
    The class `AccountGroup` is intended to facilitate dealing
    with existing accounting groups, namely Asset, Liability,
    Income, Expense, and Equity.

    The enum `AccountType` discriminates every account type,
    as stored in the database. However, many times it is preferrable
    to deal with account...
    """

    Asset     = 0
    Liability = 1
    Income    = 2
    Expense   = 3
    Equity    = 4

    @staticmethod
    def allButEquity() -> typing.Tuple[AccountGroup]:
        """Returns a tuple of all account groups except `Equity`."""

        return tuple(group for group in AccountGroup if group != AccountGroup.Equity)

    @staticmethod
    def fromAccountType(account_type: AccountType) -> AccountGroup:
        """Returns the account group which `account_type` falls under."""

        T = AccountType

        if account_type in (T.Asset, T.Cash, T.Bank, T.Receivable, T.Security):
            return AccountGroup.Asset
        elif account_type in (T.Liability, T.CreditCard, T.Payable):
            return AccountGroup.Liability
        elif account_type == T.Income:
            return AccountGroup.Income
        elif account_type == T.Expense:
            return AccountGroup.Expense
        else:
            return AccountGroup.Equity

    def accountTypes(self) -> typing.Tuple[AccountType]:
        """Returns all account types under this group."""

        T = AccountType

        if self == AccountGroup.Asset:
            return (T.Asset, T.Cash, T.Bank, T.Receivable, T.Security)
        elif self == AccountGroup.Liability:
            return (T.Liability, T.CreditCard, T.Payable)
        elif self == AccountGroup.Income:
            return (T.Income,)
        elif self == AccountGroup.Expense:
            return (T.Expense,)
        else:
            return (T.Equity,)

    def isInflow(self) -> bool:
        """Returns whether this group is an inflow group."""

        return self in (AccountGroup.Income, AccountGroup.Liability, AccountGroup.Equity)

class Account(models.AlchemicalBase):
    """Maps the SQL table `account`.
    
    The class `Account` represents an account in the account hierarchy
    stored in the database. Top-level accounts have a value of `None`
    for `parent_id`, whereas child accounts store the id of the account
    they belong to.
    
    A unique constraint is defined to ensure that parented accounts won't
    have more than one child with the same name at database level. However,
    this constraint won't work for top-level accounts, so the application
    has to enforce that top-level accounts under a same account group have
    unique names.

    The application must also ensure that the `type` of an account respects
    its `asset`, the following way. If `type` is `AccountType.Security`, then
    `asset.type` must be  `AssetType.Security`. Otherwise, `asset.type` must
    be `AssetType.Currency`. In other words, security accounts must have a
    security as their asset, and currency accounts must have a currency as
    their asset.

    See Also
    --------
    `AccountTreeModel`
    """

    __tablename__ = 'account'

    id          = sa.Column(sa.Integer,                primary_key=True, autoincrement=True)
    type        = sa.Column(sa.Enum(AccountType),      nullable=False)
    name        = sa.Column(sa.Unicode(64),            nullable=False)
    description = sa.Column(sa.Unicode(80),            nullable=False, default='')
    asset_id    = sa.Column(sa.ForeignKey('asset.id'), nullable=False)
    parent_id   = sa.Column(sa.ForeignKey('account.id'))
    precision   = sa.Column(sa.Integer)

    asset: models.Asset = sa.orm.relationship('Asset')
    parent: typing.Optional['Account'] = sa.orm.relationship('Account', remote_side=[id])

    def __init__(self,
                 type: AccountType,
                 name: str,
                 asset: models.Asset,
                 description: str = '',
                 parent: typing.Optional[Account] = None
    ) -> None:
        super().__init__()

        self.type        = type
        self.name        = name
        self.asset       = asset
        self.description = description
        self.parent      = parent

    def group(self) -> AccountGroup:
        """Returns the group this account belongs to."""

        return self.type.group()

    def extendedName(self, sep: str = ':', show_group: bool = True) -> str:
        """Returns the name of this account preceded by parent accounts in its hierarchy.
        
        If this account is a top-level account, that is, `parent` is `None`,
        behaves as follows. If `show_group` is `True`, returns this account's
        name prefixed with `group().name` and `sep`, in that order. Otherwise,
        if `show_group` is `False`, returns `name`.

        Conversely, if this account is not a top-level account, that is, `parent`
        is not `None`, recursively calls this method on `parent`, forwarding the
        given parameters, and appends `sep` and `name`, in that order, to the result.
        
        >>> banks = Account(type=AccountType.Bank, name='Banks')
        >>> banks.extendedName(sep='/', show_group=True)
        'Asset/Banks'
        >>> banks.extendedName(sep='/', show_group=False)
        'Banks'
        >>> checkings = Account(type=AccountType.Bank, name='Checkings', parent=banks)
        >>> checkings.extendedName(sep='.', show_group=True)
        'Asset.Banks.Checkings'
        >>> checkings.extendedName(sep='.', show_group=False)
        'Banks.Checkings'
        """

        if self.parent is not None:
            parent_name = self.parent.extendedName(sep=sep, show_group=show_group)
            return parent_name + sep + self.name
        elif show_group:
            return self.group().name + sep + self.name
        else:
            return self.name

    def balance(self) -> decimal.Decimal:
        """Returns the sum of quantities of all subtransactions on this account."""

        session = self.session()

        if session is None:
            return decimal.Decimal(0)

        #    SELECT s.quantity, s.quote_price, -1 AS side
        #      FROM subtransaction AS s
        #      JOIN account        AS a ON s.origin_id = a.id
        #     WHERE a.id = :account_id
        # UNION ALL 
        #    SELECT s.quantity, 1 AS quote_price, 1 AS side
        #      FROM subtransaction AS s
        #      JOIN account        AS a ON s.target_id = a.id
        #     WHERE a.id = :account_id
        
        S = sa.orm.aliased(models.Subtransaction, name='s')
        A = sa.orm.aliased(Account,               name='a')

        account_id = self.id

        s1 = (
            sa.select(S.quantity, S.quote_price, sa.literal(-1).label('side'))
              .select_from(S)
              .join(A, S.origin_id == A.id)
              .where(A.id == account_id)
        )

        s2 = (
            sa.select(S.quantity, sa.literal(1).label('quote_price'), sa.literal(1).label('side'))
              .select_from(S)
              .join(A, S.target_id == A.id)
              .where(A.id == account_id)
        )

        stmt    = s1.union_all(s2)
        results = session.execute(stmt).all()

        balance = decimal.Decimal(0)

        for quantity, quote_price, side in results:
            quantity    = decimal.Decimal(quantity) * side
            quote_price = decimal.Decimal(quote_price)
            balance     += quantity * quote_price

        return balance

    __table_args__ = (
        sa.UniqueConstraint('parent_id', 'name', name='_account_name_uc'),
    )