from __future__ import annotations
import decimal
import enum
import typing
import sqlalchemy as sa
from PyQt5      import QtCore
from mymoneyman import models

class TransactionType(enum.IntEnum):
    """Enumerates types of transaction."""

    Opening           = enum.auto()
    Income            = enum.auto()
    Expense           = enum.auto()
    CashExpense       = enum.auto()
    OnDebitExpense    = enum.auto()
    OnCreditExpense   = enum.auto()
    Deposit           = enum.auto()
    Withdrawal        = enum.auto()
    CashTransfer      = enum.auto()
    BankTransfer      = enum.auto()
    AssetTransfer     = enum.auto()
    Investment        = enum.auto()
    Divestment        = enum.auto()
    ForeignExchange   = enum.auto()
    CreditCardPayment = enum.auto()
    CreditUsage       = enum.auto()
    Repayment         = enum.auto()
    LiabilityTransfer = enum.auto()
    Split             = enum.auto()
    Undefined         = enum.auto()

    @staticmethod
    def fromAccountTypes(origin_type: models.AccountType, target_type: models.AccountType) -> TransactionType:
        T = models.AccountType

        if origin_type == T.Equity:
            return TransactionType.Opening

        elif origin_type == T.Income:
            return TransactionType.Income

        elif origin_type == T.Asset:
            if   target_type in (T.Cash, T.Bank, T.Asset): return TransactionType.AssetTransfer
            elif target_type == T.Security:                return TransactionType.Investment
            elif target_type == T.Expense:                 return TransactionType.Expense
            elif target_type in (T.Liability, T.CreditCard):
                return TransactionType.Repayment

        elif origin_type == T.Cash:
            if   target_type == T.Cash:      return TransactionType.CashTransfer
            elif target_type == T.Bank:      return TransactionType.Deposit
            elif target_type == T.Security:  return TransactionType.Investment
            elif target_type == T.Asset:     return TransactionType.AssetTransfer
            elif target_type == T.Expense:   return TransactionType.CashExpense
            elif target_type in (T.Liability, T.CreditCard):
                return TransactionType.Repayment
        
        elif origin_type == T.Bank:
            if   target_type == T.Bank:     return TransactionType.BankTransfer
            elif target_type == T.Cash:     return TransactionType.Withdrawal
            elif target_type == T.Security: return TransactionType.Investment
            elif target_type == T.Asset:    return TransactionType.AssetTransfer
            elif target_type == T.Expense:  return TransactionType.OnDebitExpense
            elif target_type in (T.Liability, T.CreditCard):
                return TransactionType.Repayment
        
        elif origin_type == T.Security:
            if target_type in (T.Cash, T.Bank, T.Asset):
                return TransactionType.Divestment

            elif target_type == T.Security:
                return TransactionType.AssetTransfer

        elif origin_type in (T.Liability, T.CreditCard):
            if target_type in (T.Cash, T.Bank, T.Security, T.Asset):
                if origin_type == T.Liability:
                    return TransactionType.CreditUsag
                else:
                    return TransactionType.CreditCardPayment

            if target_type in (T.Liability, T.CreditCard):
                return TransactionType.LiabilityTransfer

            if target_type == T.Expense:
                return TransactionType.OnCreditExpense

        return TransactionType.Undefined

class Transaction(models.AlchemicalBase):
    """Maps the SQL table `transaction`.

    The class `Transaction` is a container of subtransactions that share the
    same `date`. Detailed transaction information is stored in `Subtransaction`.

    The reason for having two transaction classes is to allow split transactions.
    A split transaction is a transaction that has more than one subtransaction.
    Split transactions are useful for when it makes sense to logically group many
    movements made between different accounts. One example is a purchase at a
    supermarket that's paid partially in cash and partially with credit card.
    While this one occurrence of buying groceries could be stored as two separate
    transactions, it makes sense to group them into one transaction since they
    happened at the same date. The method `isSplit()` checks whether a transaction
    is a split transaction.
    """

    __tablename__ = 'transaction'

    id   = sa.Column(sa.Integer,  primary_key=True, autoincrement=True)
    date = sa.Column(sa.DateTime, nullable=False)

    def __init__(self,
                 date: QtCore.QDateTime = QtCore.QDateTime.currentDateTime(),
                 subtransactions: typing.List[models.Subtransaction] = []
    ):
        super().__init__()

        self.date            = date.toPyDateTime()
        self.subtransactions = subtransactions

    def type(self) -> TransactionType:
        """Returns the type of this transaction."""

        if self.isSplit():
            return TransactionType.Split
        
        if len(self.subtransactions) == 1:
            subtransaction: models.Subtransaction = self.subtransactions[0]
            
            if isinstance(subtransaction.origin, models.Account) and isinstance(subtransaction.target, models.Account):
                return TransactionType.fromAccountTypes(
                    subtransaction.origin.type,
                    subtransaction.target.type
                )

        return TransactionType.Undefined

    def isSplit(self) -> bool:
        """Returns whether this transaction is a split transaction."""

        return len(self.subtransactions) > 1

    def relativeQuantity(self, account: models.Account) -> decimal.Decimal:
        """Sums the movements of an account on this transaction's subtransactions.

        This method will sum each movement of `account` for every subtransaction in
        this transaction, if `account` is either at the `origin` or the `target` side
        of a subtransaction.

        For example, consider a subtransaction that has accounts A and B as its origin
        and target accounts, respectively, and a quantity of 10. Assuming both accounts
        are denominated in the same asset, that means A had a decrease of 10 of its
        equity and B had an increase of 10 of its equity. Thus, if `account` was A,
        this method would return -10, for that quantity was moved out from A. If
        `account` was `B`, it would return 10, for that quantity was moved into B.
        If `account` was neither A nor B, it would return 0.

        The above procedure is applied to every subtransaction, by summing quantities,
        whether positive or negative, and accounting for subtransactions' quote prices.
        """

        quantity = decimal.Decimal(0)

        for sub in self.subtransactions:
            if account is sub.origin: quantity -= (sub.quantity * sub.quote_price)
            if account is sub.target: quantity += sub.quantity

        return round(quantity, account.precision or account.asset.precision)

    subtransactions = sa.orm.relationship('Subtransaction', back_populates='transaction', cascade='all, delete-orphan')