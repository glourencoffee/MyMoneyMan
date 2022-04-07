from __future__ import annotations
import enum
import sqlalchemy as sa
import typing
from PyQt5      import QtCore
from mymoneyman import models

class Currency(models.sql.Base):
    __tablename__ = 'currency'

    id        = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    code      = sa.Column(sa.String,  unique=True, nullable=False)
    name      = sa.Column(sa.String,  nullable=False)
    symbol    = sa.Column(sa.String,  nullable=False)
    precision = sa.Column(sa.Integer, nullable=False)
    is_fiat   = sa.Column(sa.Boolean, nullable=False)

class CurrencyTableColumn(enum.IntEnum):
    Code      = 0
    Name      = 1
    Symbol    = 2
    Precision = 3
    IsFiat    = 4

class CurrencyTableItem:
    __slots__ = (
        '_id',
        '_code',
        '_name',
        '_symbol',
        '_precision',
        '_is_fiat'
    )

    @staticmethod
    def fromSQLObject(currency: Currency) -> CurrencyTableItem:
        return CurrencyTableItem(
            id        = currency.id,
            code      = currency.code,
            name      = currency.name,
            symbol    = currency.symbol,
            precision = currency.precision,
            is_fiat   = currency.is_fiat
        )

    def __init__(self, id: int, code: str, name: str, symbol: str, precision: int, is_fiat: bool):
        self._id        = id
        self._code      = code
        self._name      = name
        self._symbol    = symbol
        self._precision = precision
        self._is_fiat   = is_fiat

    def id(self) -> int:
        return self._id

    def code(self) -> str:
        return self._code

    def name(self) -> str:
        return self._name

    def symbol(self) -> str:
        return self._symbol

    def precision(self) -> int:
        return self._precision

    def isFiat(self) -> bool:
        return self._is_fiat

    def data(self, column: CurrencyTableColumn, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None
        
        if   column == CurrencyTableColumn.Code:      return self._code
        elif column == CurrencyTableColumn.Name:      return self._name
        elif column == CurrencyTableColumn.Symbol:    return self._symbol
        elif column == CurrencyTableColumn.IsFiat:    return str(self._is_fiat)
        elif column == CurrencyTableColumn.Precision: return str(self._precision)
        else:
            return None

class CurrencyTableModel(QtCore.QAbstractTableModel):
    class SelectFilter(enum.IntFlag):
        Fiat   = 1
        Crypto = 2
        All    = Fiat|Crypto

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)

        self._items: typing.List[CurrencyTableItem] = []
    
    def select(self, filter: SelectFilter = SelectFilter.All):
        with models.sql.get_session() as session:
            stmt = sa.select(Currency)

            SelectFilter = CurrencyTableModel.SelectFilter

            if filter == SelectFilter.Fiat:
                stmt = stmt.where(Currency.is_fiat == True)
            elif filter == SelectFilter.Crypto:
                stmt = stmt.where(Currency.is_fiat == False)

            stmt = stmt.order_by(Currency.code.asc())

            results = session.execute(stmt).all()

            self.layoutAboutToBeChanged.emit()

            self._items.clear()

            for r in results:
                currency: Currency = r[0]

                self._items.append(CurrencyTableItem.fromSQLObject(currency))

            self.layoutChanged.emit()

    def exists(self, currency_code: str) -> bool:
        with models.sql.get_session() as session:
            stmt = (
                sa.select(sa.literal(1))
                  .select_from(Currency)
                  .where(Currency.code == currency_code)
            )

            result = session.execute(stmt).one_or_none()

            return result is not None

    def insert(self, code: str, name: str, symbol: str, precision: int, is_fiat: bool) -> bool:
        if self.exists(code):
            return False

        with models.sql.get_session() as session:
            currency = Currency(
                code      = code,
                name      = name,
                symbol    = symbol,
                is_fiat   = is_fiat,
                precision = precision
            )

            session.add(currency)
            session.commit()

            self.layoutAboutToBeChanged.emit()

            self._items.append(CurrencyTableItem.fromSQLObject(currency))
            self._items.sort(key=lambda item: item.code())

            self.layoutChanged.emit()

            return True

    def itemFromIndex(self, index: QtCore.QModelIndex) -> typing.Optional[CurrencyTableItem]:
        if not index.isValid():
            return None
        
        try:
            return self._items[index.row()]
        except IndexError:
            return None

    ################################################################################
    # Overloaded methods
    ################################################################################
    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        item = self.itemFromIndex(index)

        if item is None:
            return None

        return item.data(CurrencyTableColumn(index.column()), role)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.ItemDataRole.DisplayRole:
            return CurrencyTableColumn(section).name

        return None

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._items)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(CurrencyTableColumn)