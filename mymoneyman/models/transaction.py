from __future__ import annotations
import collections
import datetime
import decimal
import enum
import itertools
import typing
import sqlalchemy as sa
from PyQt5      import QtCore, QtGui
from mymoneyman import models

class Transaction(models.sql.Base):
    __tablename__ = 'transaction'

    id   = sa.Column(sa.Integer,  primary_key=True, autoincrement=True)
    date = sa.Column(sa.DateTime, nullable=False)

    subtransactions = sa.orm.relationship('Subtransaction', back_populates='transaction')

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

    transaction = sa.orm.relationship('Transaction', back_populates='subtransactions')

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

    def relativeQuantity(self, reference_account_id: int) -> decimal.Decimal:
        if reference_account_id == self._origin_account_id:
            return -self._quantity # outflow
        elif reference_account_id == self._target_account_id:
            return self._quantity # inflow
        else:
            raise ValueError(f'reference account id {reference_account_id} is neither an origin account nor a target acount')

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

    def copy(self) -> SubtransactionItem:
        return SubtransactionItem(
            self.id(),
            self.comment(),
            self.quantity(),
            self.originAccountId(),
            self.originAccountName(),
            self.originAccountType(),
            self.targetAccountId(),
            self.targetAccountName(),
            self.targetAccountType()
        )

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
    
    class Column(enum.IntEnum):
        Type          = 0 # (`TransactionType`, read-only)
        Date          = 1 # (`QDateTime`,       read-write)
        Comment       = 2 # (`str`,             read-write)
        Transference  = 3 # (`int`,             read-write)
        Inflow        = 4 # (`decimal.Decimal`, read-write)
        Outflow       = 5 # (`decimal.Decimal`, read-write)
        Balance       = 6 # (`decimal.Decimal`, read-only)

        def isReadWrite(self) -> bool:
            C = TransactionTableItem.Column
            
            return self not in (C.Type, C.Balance)

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
        if self.isSplit():
            return TransactionType.Split
        
        sub_item = self._sub_items[0]
        return TransactionType.fromAccountTypes(sub_item.originAccountType(), sub_item.targetAccountType())

    def isSplit(self) -> bool:
        return self.subtransactionCount() > 1

    def date(self) -> datetime.datetime:
        return self._date

    def balance(self) -> decimal.Decimal:
        return self._balance

    def subtransactionItems(self) -> typing.List[SubtransactionItem]:
        return self._sub_items.copy()

    def subtransactionCount(self) -> int:
        return len(self._sub_items)

    def subtransactionTotal(self, reference_account_id: int) -> decimal.Decimal:
        return sum(sub_item.relativeQuantity(reference_account_id) for sub_item in self._sub_items)

    def setData(self, reference_account_id: int, column: Column, value: typing.Any, role: int = QtCore.Qt.ItemDataRole.EditRole) -> bool:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self.setDisplayRoleData(reference_account_id, column, value)
        
        elif role == QtCore.Qt.ItemDataRole.EditRole:
            return self.setEditRoleData(reference_account_id, column, value)

        return False

    def setDisplayRoleData(self, reference_account_id: int, column: Column, value: typing.Any) -> bool:
        if self.isSplit():
            return False

        sub_item = self._sub_items[0]

        if column == TransactionTableItem.Column.Transference and isinstance(value, str):
            if reference_account_id == sub_item.originAccountId():
                if sub_item.targetAccountName() != value:
                    sub_item._target_account_name = value
                    # TODO: pass account type so we can refresh changes.
                    return True
            else:
                if sub_item.originAccountName() != value:
                    sub_item._origin_account_name = value
                    return True
        
        return False

    def setEditRoleData(self, reference_account_id: int, column: Column, value: typing.Any) -> bool:
        if self.isSplit():
            return False

        Column = TransactionTableItem.Column

        if column == Column.Date and isinstance(value, QtCore.QDateTime):
            date = value.toPyDateTime()

            if self._date == date:
                return False

            self._date = date
            return True

        sub_item = self._sub_items[0]

        if column == Column.Comment and isinstance(value, str):
            if sub_item.comment() == value or (value == '' and sub_item.comment() is None):
                return False

            sub_item._comment = value
            return True
        
        if column == Column.Transference and isinstance(value, int):
            if reference_account_id == sub_item.originAccountId():
                if sub_item.targetAccountId() == value:
                    return False

                sub_item._target_account_id = value
                return True
            else:
                if sub_item.originAccountId() == value:
                    return False

                sub_item._origin_account_id = value
                return True

        if column == Column.Inflow and isinstance(value, decimal.Decimal):
            # TODO: use account currency's decimal places when currencies is introduced
            value            = round(value, 8)
            current_quantity = sub_item.relativeQuantity(reference_account_id)

            if current_quantity >= 0:
                current_quantity = value
            else:
                current_quantity += value

                if current_quantity > 0:
                    origin_name = sub_item._origin_account_name
                    origin_type = sub_item._origin_account_type

                    sub_item._origin_account_id   = sub_item._target_account_id
                    sub_item._origin_account_name = sub_item._target_account_name
                    sub_item._origin_account_type = sub_item._target_account_type
                    sub_item._target_account_id   = reference_account_id
                    sub_item._target_account_name = origin_name
                    sub_item._target_account_type = origin_type

            # TODO: use account currency's decimal places when currencies is introduced
            current_quantity = round(abs(current_quantity), 8)

            if current_quantity == sub_item.quantity():
                return False
            
            sub_item._quantity = current_quantity

            return True

        if column == Column.Outflow and isinstance(value, decimal.Decimal):
            # TODO: use account currency's decimal places when currencies is introduced
            value            = round(-value, 8)
            current_quantity = sub_item.relativeQuantity(reference_account_id)

            if current_quantity <= 0:
                current_quantity = value
            else:
                current_quantity += value

                if current_quantity < 0:
                    target_name = sub_item._target_account_name
                    target_type = sub_item._target_account_type

                    sub_item._target_account_id   = sub_item._origin_account_id
                    sub_item._target_account_name = sub_item._origin_account_name
                    sub_item._target_account_type = sub_item._origin_account_type
                    sub_item._origin_account_id   = reference_account_id
                    sub_item._origin_account_name = target_name
                    sub_item._origin_account_type = target_type

            # TODO: use account currency's decimal places when currencies is introduced
            current_quantity = round(abs(current_quantity), 8)

            if current_quantity == sub_item.quantity():
                return False

            sub_item._quantity = current_quantity

        return False

    def data(self, reference_account_id: int, column: Column, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self.getDisplayRoleData(reference_account_id, column)
        
        elif role == QtCore.Qt.ItemDataRole.FontRole and column == TransactionTableItem.Column.Type:
            font = QtGui.QFont()
            font.setStyle(QtGui.QFont.Style.StyleItalic)
            return font
        
        elif role == QtCore.Qt.ItemDataRole.EditRole:
            return self.getEditRoleData(reference_account_id, column)
        
        return None

    def getDisplayRoleData(self, reference_account_id: int, column: Column) -> typing.Any:
        Column = TransactionTableItem.Column

        if   column == Column.Type:    return self.type().name
        elif column == Column.Date:    return str(self.date())
        elif column == Column.Balance: return str(self.balance())
        else:
            if self.isSplit():
                return '(Split)'
            
            sub_item = self._sub_items[0]

            if column == Column.Comment:
                return sub_item.comment()

            if reference_account_id == sub_item.originAccountId():
                if   column == Column.Transference: return sub_item.targetAccountName()
                elif column == Column.Inflow:       return None
                elif column == Column.Outflow:      return str(sub_item.quantity())
            else:
                if   column == Column.Transference: return sub_item.originAccountName()
                elif column == Column.Inflow:       return str(sub_item.quantity())
                elif column == Column.Outflow:      return None

            return None

    def getEditRoleData(self, reference_account_id: int, column: Column) -> typing.Any:
        Column = TransactionTableItem.Column

        if column == Column.Date:
            return QtCore.QDateTime(self.date())

        if self.isSplit():
            return None

        sub_item = self._sub_items[0]

        if column == Column.Comment: return sub_item.comment()

        if reference_account_id == sub_item.originAccountId():
            if   column == Column.Transference: return sub_item.targetAccountId()
            elif column == Column.Inflow:       return None
            elif column == Column.Outflow:      return sub_item.quantity()
        else:
            if   column == Column.Transference: return sub_item.originAccountId()
            elif column == Column.Inflow:       return sub_item.quantity()
            elif column == Column.Outflow:      return None

        return None

    def copy(self) -> TransactionTableItem:
        return TransactionTableItem(
            self.id(),
            self.date(),
            self.balance(),
            [sub_item.copy() for sub_item in self._sub_items]
        )

    def __repr__(self) -> str:
        return f"TransactionTableItem<id={self._id} type={repr(self.type())} date={repr(self._date)} balance={self._balance}>"

class _InsertableItem(TransactionTableItem):
    def __init__(self, reference_account_id: int):
        # FIXME: yeah, this is pretty ugly, having to use placeholder values, but
        #        what to do?
        sub_item = SubtransactionItem(0, '', decimal.Decimal(0), reference_account_id, '', ..., 0, '', ...)

        super().__init__(0, datetime.datetime.now(), decimal.Decimal(0), [sub_item])

    def data(self, reference_account_id: int, column: Column, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        Column = TransactionTableItem.Column

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if column == Column.Type:
                return '(New)'
            
            if column == Column.Balance:
                return None
        
        return super().data(reference_account_id, column, role)

class TransactionTableModel(QtCore.QAbstractTableModel):
    """Implements a model for manipulating transactions on the database."""

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)

        # TODO: tr()
        self._columns = ('Type', 'Date', 'Comment', 'Transference', 'Inflow', 'Outflow', 'Balance')
        self._insertable_item = None
        self._reset(None)

    def selectAccount(self, account_id: int, extended_name_sep: str = ':'):
        transactions = collections.defaultdict(list)

        with models.sql.get_session() as session:
            A = models.Account
            S = Subtransaction
            T = Transaction
            
            # WITH RECURSIVE cte(id, type, parent_id, name, is_extended) AS (
            #   SELECT id, type, parent_id, name, FALSE
            #     FROM account
            #    UNION
            #   SELECT c.id, c.type, c.parent_id, p.name || :extended_name_sep || c.name, TRUE
            #     FROM cte     AS p
            #     JOIN account AS c ON c.parent_id = p.id
            # )
            #   SELECT t.id, t.date, s.id, s.comment, s.quantity,
            #          origin.id, origin.type, (SELECT name FROM cte WHERE id = origin.id AND (parent_id IS NULL OR is_extended IS TRUE)),
            #          target.id, target.type, (SELECT name FROM cte WHERE id = target.id AND (parent_id IS NULL OR is_extended IS TRUE))
            #     FROM subtransaction AS s
            #     JOIN "transaction"  AS t      ON s.transaction_id = t.id
            #     JOIN account        AS origin ON s.origin_id      = origin.id
            #     JOIN account        AS target ON s.target_id      = target.id
            #    WHERE origin.id = :account_id OR target.id = :account_id
            # ORDER BY t.id, t.date ASC

            top_stmt = (
                sa.select(
                    A.id,
                    A.type,
                    A.parent_id,
                    A.name,
                    sa.literal(False).label('is_extended')
                  )
                  .cte('cte', recursive=True)
            )

            parent   = sa.orm.aliased(top_stmt)
            Child: A = sa.orm.aliased(A)
            
            cte = top_stmt.union(
                sa.select(
                    Child.id,
                    Child.type,
                    Child.parent_id,
                    (parent.c.name + sa.literal(extended_name_sep) + Child.name).label('name'),
                    sa.literal(True).label('is_extended')
                  )
                  .join(parent, Child.parent_id == parent.c.id)
            )

            Origin: A = sa.orm.aliased(A)
            Target: A = sa.orm.aliased(A)

            origin_name_stmt = (
                sa.select(cte.c.name)
                  .where(cte.c.id == Origin.id)
                  .where(
                      sa.or_(
                          cte.c.parent_id == None,
                          cte.c.is_extended == True
                      )
                  )
            )

            target_name_stmt = (
                sa.select(cte.c.name)
                  .where(cte.c.id == Target.id)
                  .where(
                      sa.or_(
                          cte.c.parent_id == None,
                          cte.c.is_extended == True
                      )
                  )
            )

            stmt = (
                sa.select(
                    T.id, T.date, S.id, S.comment, S.quantity,
                    Origin.id, Origin.type, origin_name_stmt.scalar_subquery(),
                    Target.id, Target.type, target_name_stmt.scalar_subquery()
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
                origin_id, origin_type, origin_name,
                target_id, target_type, target_name
            ) in result:
                origin_group = models.AccountGroup.fromAccountType(origin_type)
                target_group = models.AccountGroup.fromAccountType(target_type)

                origin_name = origin_group.name + extended_name_sep + origin_name
                target_name = target_group.name + extended_name_sep + target_name

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
        
        self._reset(account_id)
        self._insertable_item = _InsertableItem(account_id)

        balance = decimal.Decimal(0)

        for key, sub_items in transactions.items():
            transaction_id, transaction_date = key
            
            account_type = None

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

    def hasDraft(self) -> bool:
        return self._draft_item is not None

    def persistDraft(self) -> bool:
        if not self.hasDraft():
            return False

        item      = self._draft_item
        is_insert = item is self._insertable_item

        with models.sql.get_session() as session:
            if is_insert:
                subtransactions = []

                for sub_item in item.subtransactionItems():
                    s = Subtransaction(
                        comment   = sub_item.comment(),
                        origin_id = sub_item.originAccountId(),
                        target_id = sub_item.targetAccountId(),
                        quantity  = sub_item.quantity()
                    )
                    
                    subtransactions.append(s)
                    session.add(s)

                t = Transaction(date=item.date(), subtransactions=subtransactions)
                session.add(t)
            else:
                session.execute(
                    sa.update(Transaction)
                      .where(Transaction.id == item.id())
                      .values(date=item.date())
                )

                for sub_item in item.subtransactionItems():
                    session.execute(
                        sa.update(Subtransaction)
                          .where(Subtransaction.id == sub_item.id())
                          .values(
                            comment   = sub_item.comment(),
                            origin_id = sub_item.originAccountId(),
                            target_id = sub_item.targetAccountId(),
                            quantity  = sub_item.quantity()
                          )
                    )

            session.commit()

        row = self._draft_row

        # Reflect updates to the database on the model.
        if is_insert:
            self.layoutAboutToBeChanged.emit()

            self._items.append(item.copy())
            self._insertable_item = _InsertableItem(self._account_id)
            self._draft_item      = None
            self._draft_row       = -1

            self.layoutChanged.emit()
        else:
            self._items[row] = item
            self._draft_item = None
            self._draft_row  = -1

            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))

        self.updateBalances(row)

        return True

    def discardDraft(self) -> bool:
        if not self.hasDraft():
            return False

        row = self._draft_row

        if self._draft_item is self._insertable_item:
            self._insertable_item = _InsertableItem(self._account_id)

        self._draft_item = None
        self._draft_row  = -1
        self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))

        return True

    def setInsertable(self, insertable: bool):
        if self.insertable() == insertable:
            return

        self.layoutAboutToBeChanged.emit()

        if insertable:
            self._insertable_item = _InsertableItem(self._account_id)
        else:
            self._insertable_item = None

        self.layoutChanged.emit()

    def insertable(self) -> bool:
        return self._insertable_item is not None

    def updateBalances(self, start_row: int):
        if start_row == 0:
            start_balance = decimal.Decimal(0)
        else:
            start_balance = self._items[start_row - 1].balance()

        updated = False

        for item in itertools.islice(self._items, start_row, None):
            start_balance += item.subtransactionTotal(self._account_id)
            item._balance = start_balance

            updated = True

        if updated:
            column = TransactionTableItem.Column.Balance

            self.dataChanged.emit(self.index(start_row, column), self.index(self.rowCount() - 1, column))

    def itemFromIndex(self, index: QtCore.QModelIndex) -> typing.Optional[TransactionTableItem]:
        if not index.isValid():
            return None

        return self._items[index.row()]

    ################################################################################
    # Overloaded methods
    ################################################################################
    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if self._account_id is None:
            return None
        
        row = index.row()
        
        if self._draft_item is not None and self._draft_row == row:
            # If there's a draft for item at `row`, show draft instead.
            item = self._draft_item
        else:
            try:
                item: TransactionTableItem = self._items[row]
            except IndexError:
                item = self._insertable_item

        col = TransactionTableItem.Column(index.column())

        return item.data(self._account_id, col, role)

    def setData(self, index: QtCore.QModelIndex, value: typing.Any, role: int = QtCore.Qt.ItemDataRole.EditRole) -> bool:
        if self._account_id is None:
            return False

        row = index.row()
        
        try:
            item: TransactionTableItem = self._items[row]
        except IndexError:
            item = self._insertable_item

        is_new_draft = False

        if not self.hasDraft():
            # There's no editing going on, that is, no draft, so start a new one.
            self._draft_item = item if item is self._insertable_item else item.copy()
            self._draft_row  = row
            is_new_draft     = True

        elif self._draft_row != row:
            # A draft exists for an item which is not the current one being edited,
            # so ignore the editing request.
            return False

        col = TransactionTableItem.Column(index.column())

        if self._draft_item.setData(self._account_id, col, value, role):
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))
            return True
        
        # This check is for the case a draft was created for the first time, but there was
        # no change to `item`, in which case we have a "fake draft." A draft must be always
        # created by copying `item` because we don't know whether an item has changed before
        # calling `TransactionTableItem.setData()`; and after we call it, it's already too late.
        # Thus, if we created a new draft, but no changed was made to the item, we discard
        # the new draft right away.
        if is_new_draft:
            self._draft_item = None
            self._draft_row  = -1

        return False

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        if not index.isValid():
            return QtCore.Qt.ItemFlag.NoItemFlags

        flags = super().flags(index)
        col   = TransactionTableItem.Column(index.column())

        if col.isReadWrite():
            flags |= QtCore.Qt.ItemFlag.ItemIsEditable

        return flags

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self._columns[section]

        return None

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._items) + int(self.insertable())

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._columns)

    ################################################################################
    # Internals
    ################################################################################
    def _reset(self, account_id: typing.Optional[int]):
        self._account_id = account_id
        self._items      = []
        self._draft_item = None
        self._draft_row  = -1