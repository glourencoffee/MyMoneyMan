from __future__ import annotations
import collections
import enum
import datetime
import decimal
import locale
import typing
import sqlalchemy as sa
from PyQt5      import QtCore, QtGui
from mymoneyman import models

class Transaction(models.sql.Base):
    __tablename__ = 'transaction'

    id   = sa.Column(sa.Integer,  primary_key=True, autoincrement=True)
    date = sa.Column(sa.DateTime, nullable=False)

    def __repr__(self) -> str:
        return f"Transaction<id={self.id} date={self.date}>"

class Subtransaction(models.sql.Base):
    __tablename__ = 'subtransaction'

    id             = sa.Column(sa.Integer,                      primary_key=True, autoincrement=True)
    transaction_id = sa.Column(sa.ForeignKey('transaction.id'), nullable=False)
    comment        = sa.Column(sa.String)
    origin_id      = sa.Column(sa.ForeignKey('account.id'),     nullable=False)
    target_id      = sa.Column(sa.ForeignKey('account.id'),     nullable=False)
    quantity       = sa.Column(models.sql.Decimal(8),           nullable=False)

    def __repr__(self) -> str:
        return (
            "Subtransaction<"
            f"id={self.id} "
            f"transaction_id={self.transaction_id} "
            f"origin_id={self.origin_id} "
            f"target_id={self.target_id} "
            f"quantity={self.quantity}"
            ">"
        )

class TransactionType(enum.IntEnum):
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
            elif target_type == T.Security:                return TransactionType.Divestment
            elif target_type == T.Expense:                 return TransactionType.Expense

        elif origin_type == T.Cash:
            if   target_type == T.Cash:      return TransactionType.CashTransfer
            elif target_type == T.Bank:      return TransactionType.Deposit
            elif target_type == T.Security:  return TransactionType.Investment
            elif target_type == T.Asset:     return TransactionType.AssetTransfer
            elif target_type == T.Expense:   return TransactionType.CashExpense
        
        elif origin_type == T.Bank:
            if   target_type == T.Bank:     return TransactionType.BankTransfer
            elif target_type == T.Cash:     return TransactionType.Withdrawal
            elif target_type == T.Security: return TransactionType.Investment
            elif target_type == T.Asset:    return TransactionType.AssetTransfer
            elif target_type == T.Expense:  return TransactionType.OnDebitExpense
        
        elif origin_type == T.Security:
            if target_type in (T.Cash, T.Bank, T.Asset):
                return TransactionType.Divestment

            elif target_type == T.Security:
                return TransactionType.AssetTransfer

        # elif origin_type == T.Liability:
        #     return

        # if target_type == T.Liability:

        #     return TransactionType.Repayment

        return TransactionType.Undefined

class SubtransactionItem:
    __slots__ = (
        '_id',
        '_comment',
        '_quantity',
        '_origin_account_id',
        '_origin_account_name',
        '_origin_account_type',
        '_target_account_id',
        '_target_account_name',
        '_target_account_type'
    )

    def __init__(self,
                 id: int,
                 comment: str,
                 quantity: decimal.Decimal,
                 origin_account_id: int,
                 origin_account_name: str,
                 origin_account_type: models.AccountType,
                 target_account_id: int,
                 target_account_name: str,
                 target_account_type: models.AccountType
    ):
        self._id                  = id
        self._comment             = comment
        self._origin_account_id   = origin_account_id
        self._origin_account_name = origin_account_name
        self._origin_account_type = origin_account_type
        self._target_account_id   = target_account_id
        self._target_account_name = target_account_name
        self._target_account_type = target_account_type
        self._quantity            = quantity

    def id(self) -> int:
        return self._id

    def comment(self) -> str:
        return self._comment
    
    def quantity(self) -> decimal.Decimal:
        return self._quantity

    def originAccountId(self) -> int:
        return self._origin_account_id

    def originAccountName(self) -> str:
        return self._origin_account_name

    def originAccountType(self) -> models.AccountType:
        return self._origin_account_type

    def targetAccountId(self) -> int:
        return self._target_account_id

    def targetAccountName(self) -> str:
        return self._target_account_name

    def targetAccountType(self) -> models.AccountType:
        return self._target_account_type

    def __repr__(self) -> str:
        return (
            "SubtransactionItem<"
            f"id={self._id} quantity={self._quantity} "
            f"origin=(id={self._origin_account_id}, name='{self._origin_account_name}', type={repr(self._origin_account_type)}) "
            f"target=(id={self._target_account_id}, name='{self._target_account_name}', type={repr(self._target_account_type)})"
            ">"
        )

class TransactionTableItem:
    __slots__ = ('_id', '_date', '_balance', '_sub_items')

    def __init__(self, id: int, date: datetime.datetime, balance: decimal.Decimal, subtransaction_items: typing.List[SubtransactionItem]):
        if len(subtransaction_items) == 0:
            raise ValueError('transaction must have at least one subtransaction')

        self._id        = id
        self._date      = date
        self._balance   = balance
        self._sub_items = subtransaction_items

    def id(self) -> int:
        return self._id

    def type(self) -> TransactionType:
        if self.subtransactionCount() > 1:
            return TransactionType.Split
        
        sub_item = self._sub_items[0]
        return TransactionType.fromAccountTypes(sub_item.originAccountType(), sub_item.targetAccountType())

    def date(self) -> datetime.datetime:
        return self._date

    def subtransactionItems(self) -> typing.List[SubtransactionItem]:
        return self._sub_items.copy()

    def subtransactionCount(self) -> int:
        return len(self._sub_items)

    def quantity(self) -> decimal.Decimal:
        return self._quantity

    def balance(self) -> decimal.Decimal:
        return self._balance

    def __repr__(self) -> str:
        return f"TransactionTableItem<id={self._id} type={repr(self.type())} date={repr(self._date)} balance={self._balance}>"

class TransactionTableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)

        self._account_id: typing.Optional[int] = None
        self._columns = ()
        self._items = []

    def selectAll(self):
        self._account_id = None

    def selectAccount(self, account_id: int):
        transactions = collections.defaultdict(list)

        with models.sql.get_session() as session:
            A         = models.Account
            S         = Subtransaction
            T         = Transaction
            Origin: A = sa.orm.aliased(A)
            Target: A = sa.orm.aliased(A)

            #   SELECT t.id, t.date, s.id, s.comment, s.quantity
            #          origin.id, origin.name, origin.type,
            #          target.id, target.name, target.type
            #     FROM subtransaction AS s
            #     JOIN "transaction"  AS t      ON s.transaction_id = t.id
            #     JOIN account        AS origin ON s.origin_id      = origin.id
            #     JOIN account        AS target ON s.target_id      = target.id
            # ORDER BY t.id, t.date ASC

            stmt = (
                sa.select(
                    T.id, T.date, S.id, S.comment, S.quantity,
                    Origin.id, Origin.name, Origin.type,
                    Target.id, Target.name, Target.type
                  )
                  .select_from(S)
                  .join(T,      S.transaction_id == T.id)
                  .join(Origin, S.origin_id      == Origin.id)
                  .join(Target, S.target_id      == Target.id)
                  .where(
                      sa.or_(
                          Origin.id == account_id,
                          Target.id == account_id
                      )
                  )
                  .order_by(T.id.asc())
                  .order_by(T.date.asc())
            )

            result = session.execute(stmt).all()

            for (
                tra_id, tra_date, sub_id, comment, quantity,
                origin_id, origin_name, origin_type,
                target_id, target_name, target_type
             ) in result:
                sub_item = SubtransactionItem(
                    id                  = sub_id,
                    comment             = comment,
                    quantity            = quantity,
                    origin_account_id   = origin_id,
                    origin_account_name = origin_name,
                    origin_account_type = origin_type,
                    target_account_id   = target_id,
                    target_account_name = target_name,
                    target_account_type = target_type
                )

                transactions[(tra_id, tra_date)].append(sub_item)
        
        self.layoutAboutToBeChanged.emit()
        
        # TODO: tr()
        self._account_id = account_id
        self._columns = ('Type', 'Date', 'Comment', 'Transference', 'Inflow', 'Outflow', 'Balance')
        self._items = []

        balance = decimal.Decimal(0)

        for key, sub_items in transactions.items():
            transaction_id, transaction_date = key
            
            for sub_item in sub_items:
                if account_id == sub_item.originAccountId():
                    balance     -= sub_item.quantity()
                    account_type = sub_item.originAccountType()
                else:
                    balance     += sub_item.quantity()
                    account_type = sub_item.targetAccountType()
                
                AccountGroup  = models.AccountGroup
                account_group = AccountGroup.fromAccountType(account_type)

                # Reverse the balance for Equity, Income, and Liability account groups.
                #
                # Income and Equity groups make for inherently "giving" accounts: transactions
                # are never made *to* them, but always *from* them. Same goes for Liability,
                # but with a difference: Liability accounts can both be on the taking side and
                # giving side of a transaction.
                #
                # Regardless, a liability has likewise the purpose of "giving", since they
                # represent an owed responsibility. Thus, even though these accounts have negative
                # balances programmatically speaking, they are meant to be thought of as positive
                # when being presented to the user, because the user already knows that a liability
                # means a "subtraction" of his equity.
                if account_group in (AccountGroup.Equity, AccountGroup.Income, AccountGroup.Liability):
                    balance *= -1

            transaction_item = TransactionTableItem(
                id                   = transaction_id,
                date                 = transaction_date,
                balance              = balance,
                subtransaction_items = sub_items
            )

            self._items.append(transaction_item)
        
        self.layoutChanged.emit()

    def itemFromIndex(self, index: QtCore.QModelIndex) -> typing.Optional[TransactionTableItem]:
        if not index.isValid():
            return None

        return self._items[index.row()]

    def itemRowData(self, item: TransactionTableItem, column: int, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if   column == 0: return item.type().name
            elif column == 1: return str(item.date())
            elif column == 6: return locale.currency(item.balance(), grouping=True) # TODO: use account currency rather than locale
            else:
                is_split = item.type() == TransactionType.Split

                if is_split:
                    return '(Split)'
                
                sub_item = item.subtransactionItems()[0]

                if column == 2:
                    return sub_item.comment()
                
                if self._account_id == sub_item.originAccountId():
                    if   column == 3: return sub_item.targetAccountName()
                    elif column == 5: return locale.currency(sub_item.quantity(), grouping=True) # TODO: use account currency rather than locale
                else:
                    if   column == 3: return sub_item.originAccountName()
                    elif column == 4: return locale.currency(sub_item.quantity(), grouping=True) # TODO: use account currency rather than locale
        
        elif role == QtCore.Qt.ItemDataRole.FontRole and column == 0:
            font = QtGui.QFont()
            font.setStyle(QtGui.QFont.Style.StyleItalic)
            return font
        
        elif role == QtCore.Qt.ItemDataRole.EditRole and column == 1:
            return QtCore.QDateTime(item.date())
        
        return None

    def lastRowData(self, column: int, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if   column == 0: return '(New)'
            elif column == 6: return locale.currency(0) # TODO: use account currency rather than locale

        elif role == QtCore.Qt.ItemDataRole.FontRole and column == 0:
            font = QtGui.QFont()
            font.setStyle(QtGui.QFont.Style.StyleItalic)
            return font
        
        elif role == QtCore.Qt.ItemDataRole.EditRole and column == 1:
            return QtCore.QDateTime.currentDateTime()
        
        return None

    ################################################################################
    # Overloaded methods
    ################################################################################
    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if not index.isValid():
            return None
        
        row = index.row()
        col = index.column()

        try:
            item: TransactionTableItem = self._items[row]
            return self.itemRowData(item, col, role)
        except IndexError:
            return self.lastRowData(col, role)

    def setData(self, index: QtCore.QModelIndex, value: typing.Any, role: int = QtCore.Qt.ItemDataRole.EditRole) -> bool:
        print('setData(): value ==', value)
        # TODO

        return False

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        if not index.isValid():
            return QtCore.Qt.ItemFlag.NoItemFlags

        flags = super().flags(index)
        
        if index.column() in range(1, 6):
            flags |= QtCore.Qt.ItemFlag.ItemIsEditable

        return flags

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self._columns[section]

        return None

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._items) + 1

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._columns)