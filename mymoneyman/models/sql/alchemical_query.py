import sqlalchemy     as sa
import sqlalchemy.orm as sa_orm
import typing
from PyQt5        import QtCore
from PyQt5.QtCore import Qt

class AlchemicalQueryModel(QtCore.QAbstractTableModel):
    """Provides data from a SQLAlchemy query.

    The class `AlchemicalQueryModel` implements a table model that's
    populated after a SQLAlchemy select statement.

    The select statement used for the query is set with `setStatement()`,
    which causes followup calls to `select()` to populate a model instance
    with all rows from that statement.

    >>> model = AlchemicalQueryModel()
    >>> model.setStatement(sa.select(sa.literal('My Data')))
    >>> model.select(session)
    >>> model.rowCount()
    1
    >>> model.columnCount()
    1
    >>> model.data(model.index(0, 0))
    'My Data'

    See Also
    --------
    `AlchemicalTableModel`
    """

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

        self._statement = None
        self._columns   = []
        self._records   = []

    def clear(self) -> None:
        """Removes all columns and rows from this model.
        
        This model's select statement, if any, is left unchanged.
        """

        self.beginResetModel()
        self._columns.clear()
        self._records.clear()
        self.endResetModel()

    def setStatement(self, statement) -> None:
        """Sets a select statement to be used in a call to `select()`.

        All rows and columns are removed from this model.
        
        Calling this method has no effect if `statement` is same `statement()`.
        """

        if statement == self._statement:
            return

        self._statement = statement
        self.clear()
    
    def statement(self):
        """Returns the select statement used by this model, if any."""

        return self._statement

    def select(self, session: sa_orm.Session) -> None:
        """Selects rows and columns from `session` using this model's statement.
        
        If this model has no select statement, does nothing.
        """

        statement = self.statement()

        if statement is None:
            return

        result: sa.engine.Result = session.execute(statement)
        
        self.beginResetModel()
        self._columns = self.createColumns(result)
        self._records = result.all()

        self.endResetModel()

    def createColumns(self, result: sa.engine.Result) -> typing.List[str]:
        """Creates columns for a select query.
        
        This method is called by `select()` and may be overriden by
        subclasses to return custom column names other than the ones
        returned in the query by the select statement.
        """

        return list(result.keys())

    def record(self, row: int) -> tuple:
        """Returns the record at `row`.

        This method is called by `data()` to get the information that
        should be retrieved from this model. Subclasses may override it
        to return their own tuple data, if desired.
        
        Raises `IndexError` if row is not in `range(rowCount())`.
        """

        return self._records[row]

    def appendRecord(self, record: tuple) -> None:
        """Appends a record to this model.
        
        This method inserts a row at the end of this model and stores
        `record` to be given by `data()`. `record` must be a tuple of
        any size greater than 0. However, if the length of the tuple
        exceeds the number of columns of this model (`columnCount()`),
        the exceeding indices will be ignored.

        Note that no operations are performed at database level, since
        this model only deals with the database in a read-only manner.

        Raises `ValueError` if a 0-tuple is given.
        """
        if len(record) == 0:
            raise ValueError('length of tuple is 0')

        self.beginInsertRows(QtCore.QModelIndex(), self.rowCount(), self.rowCount())
        self._records.append(record)
        self.endInsertRows()

    def removeRecord(self, row: int) -> tuple:
        """Removes a record from this model.
        
        This method removes `row` from this model and returns the record
        that was stored at that row.

        Raises `IndexError` if `row` is not in `range(rowCount())`.
        """

        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        record = self._records.pop(row)
        self.endRemoveRows()

        return record

    ################################################################################
    # Overriden methods
    ################################################################################
    def index(self, row: int, column: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
        """Reimplements `QAbstractItemModel.index()`."""

        if parent.isValid() or not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        
        if row < 0 or column < 0:
            return QtCore.QModelIndex()

        return self.createIndex(row, column)
    
    def data(self, index: QtCore.QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> typing.Any:
        """Reimplements `QAbstractItemModel.data()`."""

        if index.isValid() and role == Qt.ItemDataRole.DisplayRole:
            record = self.record(index.row())

            try:
                value = record[index.column()]
            except IndexError:
                return None
            
            if value is not None:
                return str(value)

        return None

    def headerData(self,
                   section: int,
                   orientation: Qt.Orientation,
                   role: int = Qt.ItemDataRole.DisplayRole
    ) -> typing.Any:
        """Reimplements `QAbstractItemModel.headerData()`."""

        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._columns[section]
        
        return super().headerData(section, orientation, role)

    def setHeaderData(self,
                      section: int,
                      orientation: Qt.Orientation,
                      value: typing.Any,
                      role: int = Qt.ItemDataRole.DisplayRole
    ) -> None:
        """Reimplements `QAbstractItemModel.setHeaderData()`."""

        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            value = str(value)

            if self._columns[section] != value:
                self._columns[section] = value
                self.headerDataChanged.emit(orientation, section, section)
            else:
                return

        super().setHeaderData(section, orientation, value, role)

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        """Reimplements `QAbstractItemModel.rowCount()`."""

        if parent.isValid():
            return 0

        return len(self._records)
    
    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        """Reimplements `QAbstractItemModel.columnCount()`."""

        if parent.isValid():
            return 0

        return len(self._columns)