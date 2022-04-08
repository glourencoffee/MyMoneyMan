import enum
import sqlalchemy as sa
import typing
from PyQt5      import QtCore
from mymoneyman import models

class SecurityType(enum.IntEnum):
    Stock = enum.auto()
    REIT  = enum.auto()
    Bond  = enum.auto()

class Security(models.sql.Base):
    __tablename__ = 'security'

    id          = sa.Column(sa.Integer,                   primary_key=True, autoincrement=True)
    mic         = sa.Column(sa.String,                    nullable=False)
    code        = sa.Column(sa.String,                    nullable=False)
    name        = sa.Column(sa.String,                    nullable=False)
    isin        = sa.Column(sa.String,                    unique=True)
    type        = sa.Column(sa.Enum(SecurityType),        nullable=False)
    currency_id = sa.Column(sa.ForeignKey('currency.id'), nullable=False)

    currency = sa.orm.relationship('Currency', backref=sa.orm.backref('security'))

class SecurityTreeColumn(enum.IntEnum):
    Code     = 0
    Name     = 1
    ISIN     = 2
    Type     = 3
    Currency = 4

class SecurityTreeItem:
    """Stores data for child indexes at the model class `SecurityTreeModel`."""

    __slots__ = (
        '_mic',
        '_code',
        '_name',
        '_isin',
        '_type',
        '_currency_code'
    )

    def __init__(self, mic: str, code: str, name: str, isin: typing.Optional[str], type: SecurityType, currency_code: str):
        self._mic           = mic
        self._code          = code
        self._name          = name
        self._isin          = isin
        self._type          = type
        self._currency_code = currency_code

    def mic(self) -> str:
        return self._mic

    def code(self) -> str:
        return self._code

    def name(self) -> str:
        return self._name

    def isin(self) -> typing.Optional[str]:
        return self._isin

    def type(self) -> SecurityType:
        return self._type

    def currencyCode(self) -> str:
        return self._currency_code

    def data(self, column: SecurityTreeColumn, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None
        
        if   column == SecurityTreeColumn.Code:     return self._code
        elif column == SecurityTreeColumn.Name:     return self._name
        elif column == SecurityTreeColumn.ISIN:     return self._isin
        elif column == SecurityTreeColumn.Type:     return self._type.name
        elif column == SecurityTreeColumn.Currency: return self._currency_code
        else:
            return None

    def __repr__(self) -> str:
        return f"SecurityTreeItem<mic='{self._mic}' code='{self._code}' name='{self._name}' type={self._type} currency={self._currency_code}>"

class SecurityTreeTopLevelItem:
    """
    This item class stores data for top-level indexes at the model class `SecurityTreeModel`.
    Its data is composed of the Market International Code (MIC) and a list of child items.
    """

    __slots__ = ('_mic', '_children')

    def __init__(self, mic: str):
        self._mic      = mic
        self._children = []

    def mic(self) -> str:
        """Returns the MIC of this top-level item."""

        return self._mic

    def findChild(self, code: str) -> int:
        """Finds the index of a child in this top-level item by `code`.
        
        Raises `IndexError` if no child is found.
        """

        for index, child in enumerate(self._children):
            if child.code() == code:
                return index
    
        raise IndexError()

    def children(self) -> typing.List[SecurityTreeItem]:
        """Returns a shallow copy of the children of this top-level item."""

        return self._children.copy()

    def childAt(self, index: int) -> SecurityTreeItem:
        """Returns the child item at `index` of this top-level item.
        
        Raises `IndexError` if `index` is out of range.
        """
        
        return self._children[index]

    def childCount(self) -> int:
        """Returns the number of children in this top-level item."""

        return len(self._children)

    def data(self, column: SecurityTreeColumn, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole and column == SecurityTreeColumn.Code:
            return self._mic
        
        return None

    ################################################################################
    # Internals
    ################################################################################
    def _addChild(self, child: SecurityTreeItem):
        self._children.append(child)

    def _removeChild(self, index: int):
        self._children.pop(index)

    def _sort(self):
        self._children.sort(key=lambda child: child.code())

    def __repr__(self) -> str:
        return f"SecurityTreeTopLevelItem<mic='{self._mic}'>"

class SecurityTreeModel(QtCore.QAbstractItemModel):
    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)

        self._top_level_items: typing.List[SecurityTreeTopLevelItem] = []

    def clear(self):
        self.beginResetModel()
        self._top_level_items.clear()
        self.endResetModel()

    def select(self, mic: typing.Optional[str] = None):
        with models.sql.get_session() as session:
            S = sa.orm.aliased(Security,        name='s')
            C = sa.orm.aliased(models.Currency, name='c')

            stmt = (
                sa.select(
                    S.mic,
                    S.code,
                    S.name,
                    S.isin,
                    S.type,
                    C.code.label('currency_code')
                  )
                  .select_from(S)
                  .join(C, S.currency_id == C.id)
                  .order_by(S.mic.asc(), S.code.asc())
            )

            if mic is not None and mic != '':
                stmt = stmt.where(S.mic == mic)

            results = session.execute(stmt).all()
            current_market_item: typing.Optional[SecurityTreeTopLevelItem] = None

            self.clear()
            self.layoutAboutToBeChanged.emit()

            for res in results:
                mic = res[0]

                if current_market_item is None or current_market_item.mic() != mic:
                    current_market_item = SecurityTreeTopLevelItem(mic)
                    self._top_level_items.append(current_market_item)
                
                child = SecurityTreeItem(*res)

                current_market_item._addChild(child)

            self.layoutChanged.emit()

    def exists(self, mic: str, code: str) -> bool:
        with models.sql.get_session() as session:
            stmt = (
                sa.select(sa.literal(1))
                  .select_from(Security)
                  .where(Security.mic == mic)
                  .where(Security.code == code)
            )

            result = session.execute(stmt).one_or_none()

            return result is not None

    def insert(self, mic: str, code: str, name: str, isin: typing.Optional[str], type: SecurityType, currency_code: str) -> bool:
        if self.exists(mic, code):
            return False

        with models.sql.get_session() as session:
            currency = session.query(models.Currency).where(models.Currency.code == currency_code).one_or_none()

            if currency is None:
                return False

            security = Security(
                mic      = mic,
                code     = code,
                name     = name,
                isin     = isin,
                type     = type,
                currency = currency
            )

            session.add(security)
            session.commit()

            parent_item = None

            for item in self._top_level_items:
                if item.mic() == mic:
                    parent_item = item
                    break
            
            self.layoutAboutToBeChanged.emit()

            if parent_item is None:
                parent_item = SecurityTreeTopLevelItem(mic)

                self._top_level_items.append(parent_item)
                self._top_level_items.sort(key=lambda item: item.mic())

            child = SecurityTreeItem(mic, code, name, isin, type, currency_code)

            parent_item._addChild(child)
            parent_item._sort()

            self.layoutChanged.emit()

            return True

    def delete(self, mic: str, code: typing.Optional[str] = None) -> bool:
        with models.sql.get_session() as session:
            cnt_stmt = sa.select(sa.func.count()).where(Security.mic == mic)
            del_stmt = sa.delete(Security).where(Security.mic == mic)

            if code is not None:
                cnt_stmt = cnt_stmt.where(Security.code == code)
                del_stmt = del_stmt.where(Security.code == code)

            count = session.execute(cnt_stmt).first()

            if count == 0:
                return False

            session.execute(del_stmt)
            session.commit()

            parent_item     = None
            parent_item_row = -1
            
            for row, item in enumerate(self._top_level_items):
                if item.mic() == mic:
                    parent_item     = item
                    parent_item_row = row
                    break
            
            if parent_item is not None:
                should_remove_parent = False

                if code is not None:
                    try:
                        # Look up index of a child item with `code`.
                        child_row = parent_item.findChild(code)

                        # Child found. Remove it from the parent item.
                        self.beginRemoveRows(self.index(parent_item_row, 0), child_row, child_row)
                        parent_item._removeChild(child_row)
                        self.endRemoveRows()

                        # Remove parent from the model as well if it has no children
                        if parent_item.childCount() == 0:
                            should_remove_parent = True

                    except IndexError:
                        # No child item found in this model.
                        pass
                else:
                    should_remove_parent = True
                
                if should_remove_parent:
                    self.beginRemoveRows(QtCore.QModelIndex(), parent_item_row, parent_item_row)
                    self._top_level_items.remove(parent_item)
                    self.endRemoveRows()

            return True

    def marketCodes(self) -> typing.List[str]:
        return [item.mic() for item in self._top_level_items]

    def isTopLevelIndex(self, index: QtCore.QModelIndex) -> bool:
        return index.isValid() and not index.parent().isValid()

    def itemFromIndex(self, index: QtCore.QModelIndex) -> typing.Union[SecurityTreeTopLevelItem, SecurityTreeItem, None]:
        if not index.isValid():
            return None
        
        return index.internalPointer()

    ################################################################################
    # Overloaded methods
    ################################################################################
    def index(self, row: int, column: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        if not parent.isValid():
            item = self._top_level_items[row]
        else:
            parent_item: SecurityTreeTopLevelItem = parent.internalPointer()
            item = parent_item.childAt(row)
        
        return self.createIndex(row, column, item)

    def parent(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        if not index.isValid():
            return QtCore.QModelIndex()

        child_item = index.internalPointer()

        if isinstance(child_item, SecurityTreeItem):
            for row, parent_item in enumerate(self._top_level_items):
                if parent_item.mic() == child_item.mic():
                    return self.createIndex(row, 0, parent_item)

        return QtCore.QModelIndex()

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if not index.isValid():
            return None
        
        item: typing.Union[SecurityTreeTopLevelItem, SecurityTreeItem] = index.internalPointer()

        return item.data(SecurityTreeColumn(index.column()), role)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.ItemDataRole.DisplayRole:
            return SecurityTreeColumn(section).name

        return None

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if not parent.isValid():
            return len(self._top_level_items)
        else:
            item = parent.internalPointer()

            if isinstance(item, SecurityTreeTopLevelItem):
                return item.childCount()
            else:
                return 0

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(SecurityTreeColumn)