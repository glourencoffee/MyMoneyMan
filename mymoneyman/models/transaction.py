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

    subtransactions = sa.orm.relationship('Subtransaction', back_populates='transaction', cascade='all, delete-orphan')

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

class TransactionTableColumn(enum.IntEnum):
    Type          = 0 # (`TransactionType`, read-only)
    Date          = 1 # (`QDateTime`,       read-write)
    Comment       = 2 # (`str`,             read-write)
    Transference  = 3 # (`int`,             read-write)
    Inflow        = 4 # (`decimal.Decimal`, read-write)
    Outflow       = 5 # (`decimal.Decimal`, read-write)
    Balance       = 6 # (`decimal.Decimal`, read-only)

    def isReadWrite(self) -> bool:
        C = TransactionTableColumn
        
        return self not in (C.Type, C.Balance)

class TransactionTableItem:
    """Stores information of a transaction on `TransactionTableModel`."""

    __slots__ = (
        '_id',
        '_sub_id',
        '_date',
        '_comment',
        '_ref_account',
        '_transfer_account',
        '_quantity',
        '_balance'
    )

    def __init__(self,
                 id: int,
                 subtransaction_id: typing.Optional[int],
                 date: datetime.datetime,
                 comment: typing.Optional[str],
                 reference_account: typing.Optional[models.AccountInfo],
                 transference_account: typing.Optional[models.AccountInfo],
                 quantity: decimal.Decimal,
                 balance: decimal.Decimal
    ):
        self._id               = id
        self._sub_id           = subtransaction_id
        self._date             = date
        self._comment          = comment
        self._ref_account      = reference_account
        self._transfer_account = transference_account
        self._quantity         = quantity
        self._balance          = balance

    def id(self) -> int:
        return self._id

    def subtransactionId(self) -> typing.Optional[int]:
        return self._sub_id

    def type(self) -> TransactionType:
        if self.isSplit():
            return TransactionType.Split
        elif self._ref_account is not None:
            return TransactionType.fromAccountTypes(self.originAccount().type, self.targetAccount().type)
        else:
            return TransactionType.Undefined

    def date(self) -> datetime.datetime:
        return self._date

    def comment(self) -> typing.Optional[str]:
        return self._comment

    def referenceAccount(self) -> typing.Optional[models.AccountInfo]:
        return self._ref_account

    def transferenceAccount(self) -> typing.Optional[models.AccountInfo]:
        return self._transfer_account

    def originAccount(self) -> typing.Optional[models.AccountInfo]:
        if self._ref_account is None or self._transfer_account is None:
            return None
        
        if self.isInflow():
            return self._transfer_account
        else:
            return self._ref_account

    def targetAccount(self) -> typing.Optional[models.AccountInfo]:
        if self._ref_account is None or self._transfer_account is None:
            return None
        
        if self.isInflow():
            return self._ref_account
        else:
            return self._transfer_account

    def quantity(self) -> decimal.Decimal:
        return self._quantity

    def balance(self) -> decimal.Decimal:
        return self._balance

    def isSplit(self) -> bool:
        return self._transfer_account is None

    def isInflow(self) -> bool:
        return self._quantity >= 0

    def flags(self, column: TransactionTableColumn) -> QtCore.Qt.ItemFlags:
        flags = QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable
        
        if (not self.isSplit()) and column.isReadWrite():
            flags |= QtCore.Qt.ItemFlag.ItemIsEditable

        return flags

    def setData(self, column: TransactionTableColumn, value: typing.Any, role: int = QtCore.Qt.ItemDataRole.EditRole) -> bool:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self.setDisplayRoleData(column, value)
        
        elif role == QtCore.Qt.ItemDataRole.EditRole:
            return self.setEditRoleData(column, value)

        return False

    def setDisplayRoleData(self, column: TransactionTableColumn, value: typing.Any) -> bool:
        if self.isSplit():
            return False

        if (
            column == TransactionTableColumn.Transference and
            isinstance(value, str) and
            self.transferenceAccount().name != value
        ):
            self._transfer_account = self._transfer_account._replace(name=value)
            # TODO: pass account type so we can refresh changes.
            return True
        
        return False

    def setEditRoleData(self, column: TransactionTableColumn, value: typing.Any) -> bool:
        if self.isSplit():
            return False

        Column = TransactionTableColumn

        if column == Column.Date and isinstance(value, QtCore.QDateTime):
            date = value.toPyDateTime()

            if self._date == date:
                return False

            self._date = date
            return True

        if column == Column.Comment and (isinstance(value, str) or value is None):
            if self._comment == value:
                return False

            self._comment = value
            return True
        
        if column == Column.Transference and isinstance(value, int) and self._transfer_account.id != value:
            self._transfer_account = self._transfer_account._replace(id=value)
            return True

        if column in (Column.Inflow, Column.Outflow) and isinstance(value, decimal.Decimal):
            # TODO: use account currency's decimal places when currencies is introduced
            value = round(value, 8)

            if column == Column.Inflow:
                is_inflow        = value >= 0
                is_flow_reversed = is_inflow == False
            else:
                is_inflow        = value < 0
                is_flow_reversed = is_inflow == True

            value    = abs(value)
            quantity = self._quantity

            if quantity >= 0:
                if is_inflow:
                    if is_flow_reversed:
                        quantity += value
                    else:
                        quantity = value
                else:
                    quantity -= value
            else:
                if is_inflow:
                    quantity += value
                else:
                    if is_flow_reversed:
                        quantity -= value
                    else:
                        quantity = -value

            # TODO: use account currency's decimal places when currencies is introduced
            quantity = round(quantity, 8)

            if quantity == self.quantity():
                return False
            
            self._quantity = quantity
            return True

        return False

    def data(self, column: TransactionTableColumn, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self.getDisplayRoleData(column)
        
        elif role == QtCore.Qt.ItemDataRole.FontRole:
            C = TransactionTableColumn

            if column == C.Type or (self.isSplit() and column in (C.Comment, C.Transference)):
                font = QtGui.QFont()
                font.setStyle(QtGui.QFont.Style.StyleItalic)
                return font
        
        elif role == QtCore.Qt.ItemDataRole.EditRole:
            return self.getEditRoleData(column)
        
        return None

    def getDisplayRoleData(self, column: TransactionTableColumn) -> typing.Any:
        Column = TransactionTableColumn

        if   column == Column.Type:         return self.type().name
        elif column == Column.Date:         return QtCore.QDateTime(self.date()).toString('dd/MM/yyyy hh:mm:ss') # FIXME: let format be customizable
        elif column == Column.Comment:      return '-- Split Transaction --' if self.isSplit()      else self.comment()
        elif column == Column.Transference: return '-- Many --'              if self.isSplit()      else self.transferenceAccount().name
        elif column == Column.Inflow:       return str(self.quantity())      if self.quantity() > 0 else None
        elif column == Column.Outflow:      return str(abs(self.quantity())) if self.quantity() < 0 else None
        elif column == Column.Balance:      return str(self.balance())
        else:
            return None

    def getEditRoleData(self, column: TransactionTableColumn) -> typing.Any:
        Column = TransactionTableColumn

        if   column == Column.Date:         return QtCore.QDateTime(self.date())
        elif column == Column.Comment:      return self.comment()
        elif column == Column.Transference: return None if self.isSplit() else self.transferenceAccount().id
        elif column == Column.Inflow:       return self.quantity()      if self.quantity() > 0 else None
        elif column == Column.Outflow:      return abs(self.quantity()) if self.quantity() < 0 else None
        else:
            return None

    def copy(self, reference_account: models.AccountInfo) -> TransactionTableItem:
        return TransactionTableItem(
            self.id(),
            self.subtransactionId(),
            self.date(),
            self.comment(),
            reference_account,
            self.transferenceAccount(),
            self.quantity(),
            self.balance()
        )

    def __repr__(self) -> str:
        return f"TransactionTableItem<id={self._id} type={repr(self.type())} date={repr(self._date)} balance={self._balance}>"

class _InsertableItem(TransactionTableItem):
    def __init__(self):
        super().__init__(
            0,
            None,
            QtCore.QDateTime.currentDateTime().toPyDateTime(),
            None,
            ...,
            models.AccountInfo(0, '', models.AccountType.Asset),
            decimal.Decimal(0),
            decimal.Decimal(0)
        )

    def data(self, column: TransactionTableColumn, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        Column = TransactionTableColumn

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if column == Column.Type:
                return '(New)'
            
            if column == Column.Balance:
                return None
        
        return super().data(column, role)

class TransactionTableModel(QtCore.QAbstractTableModel):
    """Implements a model for manipulating transactions on the database.
    
    This class is designed to work with one account at a time. As such, it only
    deals with transaction operations for that account. The id of the associated
    account, if any, is given by `accountId()`.

    The method `selectAccount()` retrieves transactions related to a particular
    account and stores them in the model. Information about each transaction may
    be accessed by calling `data()`, or changed by calling `setData()`.

    Beside an account's transactions, this class also provides the ability to
    insert transactions on the associated account. An instance of this class can
    be made insertable or non-insertable by calling `setInsertable()`.
    
    An insertable model will enable a *draft row*, which is a row that allows a
    draft transaction to be created.
    
    A *draft transaction* is a non-persisted transaction that may be accessed and
    modified with `data()` and `setData()`, respectively, as with any transaction.
    However, a draft transaction is NOT persisted until `persistDraft()` is called.
    A draft transaction may also be discard with `discardDraft()`, in which case a
    draft row will be reset to its original state. To check whether this model has
    an active draft transaction, call `hasDraft()`.
    """

    draftStateChanged = QtCore.pyqtSignal(bool)

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)

        # TODO: tr()
        self._columns = ('Type', 'Date', 'Comment', 'Transference', 'Inflow', 'Outflow', 'Balance')
        self._insertable_item = None
        self._reset(None)

    def reset(self):
        """Dissociates this model from an account, if any."""

        if self._account is None:
            return

        self.beginResetModel()
        self._reset(None)

        if self.insertable():
            self._insertable_item = _InsertableItem()

        self.endResetModel()

    def account(self) -> typing.Optional[models.AccountInfo]:
        """
        Returns information of the account which this model is associated with,
        or `None` if this model is not associated with any account.
        """

        return self._account

    def selectAccount(self, account_id: int):
        """Retrieves transactions from the account whose id is `account_id`."""

        transactions = collections.defaultdict(list)
        account_info = None

        with models.sql.get_session() as session:
            A = models.Account
            
            account_info = session.query(A.name, A.type).where(A.id == account_id).one_or_none()

            if account_info is None:
                return

            account_name = account_info[0]
            account_type = account_info[1]
            account_info = models.AccountInfo(account_id, account_name, account_type)

            ################################################################################
            #   SELECT *
            #     FROM (
            #   SELECT t.id, t.date, s.id, s.comment, -s.quantity,
            #          target.id, target.type, target.name
            #     FROM subtransaction        AS s
            #     JOIN "transaction"         AS t      ON s.transaction_id = t.id
            #     JOIN account               AS origin ON s.origin_id      = origin.id
            #     JOIN extended_account_view AS target ON s.target_id      = target.id
            #    WHERE origin.id = :account_id
            #    UNION
            #   SELECT t.id, t.date, s.id, s.comment, s.quantity,
            #          origin.id, origin.type, origin.name
            #     FROM subtransaction        AS s
            #     JOIN "transaction"         AS t      ON s.transaction_id = t.id
            #     JOIN extended_account_view AS origin ON s.origin_id      = origin.id
            #     JOIN account               AS target ON s.target_id      = target.id
            #    WHERE target.id = :account_id
            # )
            # ORDER BY date, id ASC
            ################################################################################
            S       = Subtransaction
            T       = Transaction
            Origin  = sa.orm.aliased(A)
            Target  = sa.orm.aliased(A)
            XOrigin = sa.orm.aliased(models.ExtendedAccountView)
            XTarget = sa.orm.aliased(models.ExtendedAccountView)

            union = sa.union(
                (
                    sa.select(
                        T.id, T.date, S.id, S.comment, -S.quantity,
                        XTarget.id, XTarget.type, XTarget.name
                    )
                    .select_from(S)
                    .join(T,       S.transaction_id == T.id)
                    .join(Origin,  S.origin_id      == Origin.id)
                    .join(XTarget, S.target_id      == XTarget.id)
                    .where(Origin.id == account_id)
                ),
                (
                    sa.select(
                        T.id, T.date, S.id, S.comment, S.quantity,
                        XOrigin.id, XOrigin.type, XOrigin.name
                    )
                    .select_from(S)
                    .join(T,       S.transaction_id == T.id)
                    .join(XOrigin, S.origin_id      == XOrigin.id)
                    .join(Target,  S.target_id      == Target.id)
                    .where(Target.id == account_id)
                )
            )

            main_stmt = union.select().order_by(union.c.date.asc(), union.c.id.asc())

            result = session.execute(main_stmt).all()

            for (tra_id, tra_date, sub_id, comment, quantity, acc_id, acc_type, acc_name) in result:
                group        = models.AccountGroup.fromAccountType(acc_type)
                acc_ext_name = group.name + ':' + acc_name
                transfer_acc = models.AccountInfo(acc_id, acc_ext_name, acc_type)

                transactions[(tra_id, tra_date)].append((sub_id, comment, transfer_acc, quantity))
        
        self.layoutAboutToBeChanged.emit()
        
        self._reset(account_info)
        self._insertable_item = _InsertableItem()

        AccountGroup  = models.AccountGroup
        account_group = AccountGroup.fromAccountType(account_info.type)
        balance       = decimal.Decimal(0)

        for key, sub_items in transactions.items():
            transaction_id, transaction_date = key
            
            if len(sub_items) > 1:
                sub_id           = None
                comment          = None
                transfer_account = None
                quantity         = sum(t[3] for t in sub_items)
            else:
                sub_id, comment, transfer_account, quantity = sub_items[0]
            
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
                balance -= quantity
            else:
                balance += quantity

            transaction_item = TransactionTableItem(
                id                   = transaction_id,
                subtransaction_id    = sub_id,
                date                 = transaction_date,
                comment              = comment,
                reference_account    = account_info,
                transference_account = transfer_account,
                quantity             = quantity,
                balance              = balance
            )

            self._items.append(transaction_item)
        
        self.layoutChanged.emit()

    def hasDraft(self) -> bool:
        return self._draft_item is not None

    def removeTransaction(self, transaction_id: int) -> bool:
        """Removes a transaction from the database given its id.
        
        This method removes the referred transaction without checking whether it belongs
        to the account associated with this model.

        However, if the transaction does belong to the associated account, then that
        transaction is removed from this model after it's deleted from the database.

        Returns `True` if a transaction was deleted, and `False` otherwise.
        """

        with models.sql.get_session() as session:
            t = session.query(Transaction).filter_by(id=transaction_id).first()

            if t is None:
                return False

            session.delete(t)
            session.commit()
        
        index = self.indexFromId(transaction_id)
        item  = self.itemFromIndex(index)

        if item is None:
            # No change on the model.
            return True

        self.layoutAboutToBeChanged.emit()

        if item is self._draft_item:
            # A draft for `transaction_id` was found in the model. Let there be no draft.
            self._resetDraft()
        
        try:
            # Retrieves the item at the index row. Note that this will return
            # the original item, not the draft, as the draft will have already
            # been reset at this point. So, regardless if the row `index.row()`
            # had a draft or not, remove the item at it.
            item = self._items[index.row()]

            self._items.remove(item)
        except (IndexError, ValueError):
            pass

        self._updateBalances(index.row(), emit_data_changed=False)
        self.layoutChanged.emit()
        
        return True

    def persistDraft(self) -> bool:
        if not self.hasDraft():
            return False

        is_insert = self._draft_item is self._insertable_item

        if is_insert:
            self._insertDraft()
        else:
            self._updateDraft()
        
        return True

    def discardDraft(self) -> bool:
        if not self.hasDraft():
            return False

        row = self._draft_row

        if self._draft_item is self._insertable_item:
            self._insertable_item = _InsertableItem()

        self._resetDraft()
        self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))
        self.draftStateChanged.emit(False)

        return True

    def setInsertable(self, insertable: bool):
        """Enables or disables draft transactions on this model."""

        if self.insertable() == insertable:
            return

        self.layoutAboutToBeChanged.emit()

        if insertable:
            self._insertable_item = _InsertableItem()
        else:
            self._insertable_item = None

        self.layoutChanged.emit()

    def insertable(self) -> bool:
        """Returns whether this model allows draft transactions."""

        return self._insertable_item is not None

    def insertableRow(self) -> int:
        if self.insertable():
            return self.rowCount() - 1
        else:
            return -1

    def itemFromIndex(self, index: QtCore.QModelIndex) -> typing.Optional[TransactionTableItem]:
        """Returns the transaction item at `index`, or `None` if `index` is invalid."""

        if not index.isValid():
            return None

        if index.row() == self._draft_row:
            return self._draft_item

        try:
            return self._items[index.row()]
        except IndexError:
            return self._insertable_item

    def indexFromId(self, transaction_id: int) -> QtCore.QModelIndex:
        """
        Returns the index for the transaction identified by `transaction_id`,
        or an invalid index is there's no such transaction in this model.
        """

        for row in range(self.rowCount()):
            item = self._items[row]

            if item.id() == transaction_id:
                return self.index(row, 0)
        
        return QtCore.QModelIndex()

    ################################################################################
    # Overloaded methods
    ################################################################################
    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if self._account is None:
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

        col = TransactionTableColumn(index.column())

        return item.data(col, role)

    def setData(self, index: QtCore.QModelIndex, value: typing.Any, role: int = QtCore.Qt.ItemDataRole.EditRole) -> bool:
        if self._account is None:
            return False

        row = index.row()
        
        try:
            item: TransactionTableItem = self._items[row]
        except IndexError:
            item = self._insertable_item

        is_new_draft = False

        if not self.hasDraft():
            # There's no editing going on, that is, no draft, so start a new one.
            self._draft_item = item if item is self._insertable_item else item.copy(self._account)
            self._draft_row  = row
            is_new_draft     = True

        elif self._draft_row != row:
            # A draft exists for an item which is not the current one being edited,
            # so ignore the editing request.
            return False

        col = TransactionTableColumn(index.column())

        if self._draft_item.setData(col, value, role):
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))

            if is_new_draft:
                self.draftStateChanged.emit(True)

            return True
        
        # This check is for the case a draft was created for the first time, but there was
        # no change to `item`, in which case we have a "fake draft." A draft must be always
        # created by copying `item` because we don't know whether an item has changed before
        # calling `TransactionTableItem.setData()`; and after we call it, it's already too late.
        # Thus, if we created a new draft, but no changed was made to the item, we discard
        # the new draft right away.
        if is_new_draft:
            self._resetDraft()

        return False

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        item = self.itemFromIndex(index)

        if item is None:
            return QtCore.Qt.ItemFlag.NoItemFlags

        return item.flags(TransactionTableColumn(index.column()))

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
    def _reset(self, account: typing.Optional[models.AccountInfo]):
        self._account = account
        self._items   = []
        self._resetDraft()
    
    def _resetDraft(self):
        self._draft_item = None
        self._draft_row  = -1

    def _insertDraft(self):
        item = self._draft_item.copy(self._account)

        with models.sql.get_session() as session:
            s = Subtransaction(
                comment   = item.comment(),
                origin_id = item.originAccount().id,
                target_id = item.targetAccount().id,
                quantity  = item.quantity()
            )
                
            t = Transaction(date=item.date(), subtransactions=[s])
            
            session.add(t)
            session.add(s)
            session.commit()

            transaction_id = t.id
            
        self.layoutAboutToBeChanged.emit()

        item._id = transaction_id

        # TODO: sort list by date
        self._items.append(item)
        self._insertable_item = _InsertableItem()
        
        row = self._draft_row
        self._resetDraft()

        self.layoutChanged.emit()
        
        self.draftStateChanged.emit(False)
        self._updateBalances(row)
    
    def _updateDraft(self):
        item = self._draft_item

        with models.sql.get_session() as session:
            session.execute(
                sa.update(Transaction)
                    .where(Transaction.id == item.id())
                    .values(date=item.date())
            )

            session.execute(
                sa.update(Subtransaction)
                    .where(Subtransaction.id == item.subtransactionId())
                    .values(
                        comment   = item.comment(),
                        origin_id = item.originAccount().id,
                        target_id = item.targetAccount().id,
                        quantity  = item.quantity()
                    )
            )

            session.commit()

        row = self._draft_row

        # TODO: maybe sort list by date, if date changed
        self._items[row] = item
        self._resetDraft()

        self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))

        self.draftStateChanged.emit(False)
        self._updateBalances(row)

    def _updateBalances(self, start_row: int, emit_data_changed: bool = True):
        if start_row == 0:
            start_balance = decimal.Decimal(0)
        else:
            start_balance = self._items[start_row - 1].balance()

        updated = False

        for item in itertools.islice(self._items, start_row, None):
            start_balance += item._quantity
            item._balance = start_balance

            updated = True

        if updated and emit_data_changed:
            column = TransactionTableColumn.Balance

            self.dataChanged.emit(self.index(start_row, column), self.index(self.rowCount() - 1, column))