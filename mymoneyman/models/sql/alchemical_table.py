import sqlalchemy     as sa
import sqlalchemy.orm as sa_orm
import typing
from PyQt5      import QtCore
from mymoneyman import models

class AlchemicalTableModel(models.AlchemicalQueryModel):
    """Provides data from a SQLAlchemy mapped class.
    
    The class `AlchemicalTableModel` extends `AlchemicalQueryModel` to implement
    a table model that has all columns and all rows of a SQLAlchemy mapped class
    (`AlchemicalBase`).

    An instance of this class takes a mapped class upon construction, which may be
    later retrieved with `mappedClass()` or changed with `setMappedClass()`. This
    mapped class is used to fetch SQL rows and to type-check modifying operations
    on the database, such as `insert()` and `delete()`. Note that this class never
    commits or rolls back changes to the database.

    The method `select()` is overriden such that calls to it will store the session
    object passed in as parameter, which may be accessed later with `session()`.
    Modifying operations on the database are executed against that session.

    See Also
    --------
    `AlchemicalBase`
    `AlchemicalQueryModel`
    """

    def __init__(self,
                 mapped_cls: typing.Type[models.AlchemicalBase],
                 parent: typing.Optional[QtCore.QObject] = None
    ) -> None:
        super().__init__(parent=parent)

        self._session    = sa_orm.Session()
        self._mapped_cls = mapped_cls

        super().setStatement(sa.select(mapped_cls))

    def session(self) -> sa_orm.Session:
        """Returns the session associated with this model."""

        return self._session

    def setMappedClass(self, mapped_cls: typing.Type[models.AlchemicalBase]) -> None:
        """Changes the mapped class used by this model.
        
        This method has no effect if `mapped_cls` is same as `mappedClass()`.
        """

        if self._mapped_cls is mapped_cls:
            return

        self.clear()
        self._mapped_cls = mapped_cls

    def mappedClass(self) -> typing.Type[models.AlchemicalBase]:
        """Returns the mapped class used by this model."""

        return self._mapped_cls

    def columnIndex(self, column: sa.Column) -> int:
        """
        Returns the index of `column` in this model if `column` is a
        column of `mappedClass()`, and -1 otherwise.
        """

        try:
            return self.mappedClass().columnNames().index(column.name)
        except ValueError:
            return -1

    def rowOf(self, instance: models.AlchemicalBase) -> int:
        """
        Returns the row at which `instance` is located in this model,
        or -1 if `instance` is not in this model.
        """

        for row in range(self.rowCount()):
            if self.mappedObject(row) is instance:
                return row

        return -1

    def mappedObject(self, row: int) -> models.AlchemicalBase:
        """Returns the mapped object which is at `row` in this model.
        
        Raises `IndexError` if `row` is not in the range [0, `rowCount()`).
        """

        t = super().record(row)

        return t[0]

    def mappedObjects(self) -> typing.Generator[models.AlchemicalBase, None, None]:
        """Returns a generator that calls `mappedObject()` for every row in this model."""

        return (self.mappedObject(row) for row in range(self.rowCount()))

    def find(self, key: typing.Callable[[models.AlchemicalBase], bool]) -> typing.Optional[models.AlchemicalBase]:
        """
        Searchs for a mapped object in this model that, when passed in
        as an argument to `key`, results in `key` returning `True`.
        
        Returns `None` if `key` returns `False` for all mapped objects
        in this model.
        """

        for mapped_obj in self.mappedObjects():
            if key(mapped_obj):
                return mapped_obj
        
        return None

    def existsWith(self, key: typing.Callable[[models.AlchemicalBase], bool]) -> bool:
        """Effectively calls `find(key)` and returns whether a mapped object was found."""

        return self.find(key) is not None

    def exists(self, mapped_object: models.AlchemicalBase) -> bool:
        """Returns whether `mapped_object` is in this model.
        
        Note that this method does not check whether `mapped_object` is
        in `session()`. It is possible for a mapped object to be in the
        session of this model but yet not be part of this model, which
        may happen if that mapped object was inserted into a different
        model that uses the same session.

        >>> m1 = AlchemicalTableModel()
        >>> m1.setMappedClass(MyMappedClass)
        >>> m1.select(session)
        >>> m2 = AlchemicalTableModel()
        >>> m2.setMappedClass(MyMappedClass)
        >>> m2.select(session)
        >>> obj = MyMappedClass()
        >>> m1.insert(obj)
        >>> m1.exists(obj)
        True
        >>> m2.exists(obj)
        False
        """

        return mapped_object in self.mappedObjects()

    def insert(self, mapped_object: models.AlchemicalBase) -> bool:
        """Inserts a mapped object into this model.

        If `mapped_object` is not an instance of `mappedClass()`, returns `False`.
        
        If `mapped_object` already exists in this model, returns `False`.
        
        Otherwise, inserts `mapped_object` into this model and this model's
        `session()`, and returns `True`. Note that if that mapped object is
        already in `session()`, this method will only insert it into this model.
        """

        if not isinstance(mapped_object, self.mappedClass()):
            return False
        
        if self.exists(mapped_object):
            return False
        
        # Check before adding to session to avoid calling `Session.flush()`
        # if model has already been added, since `Session.flush()` would
        # then be the responsibility of `AlchemicalTableModel.update()`.
        if mapped_object not in self._session:
            self._session.add(mapped_object)
            self._session.flush([mapped_object])

        super().appendRecord((mapped_object,))

        return True

    def update(self, mapped_object: models.AlchemicalBase) -> bool:
        """Updates a mapped object on this model."""

        row = self.rowOf(mapped_object)
        
        if row == -1:
            return False

        self._session.flush([mapped_object])
        self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))

        return True
    
    def upsert(self, mapped_object: models.AlchemicalBase) -> bool:
        """Inserts or updates a mapped object into this model.
        
        Tries to insert `mapped_object` into this model. If the insertion
        succeeds, returns `True`.

        Otherwise, tries to update `mapped_object` on this model. Returns
        `True` if this model was updated, and `False` otherwise.
        """

        if self.insert(mapped_object):
            return True

        return self.update(mapped_object)

    def delete(self, mapped_object: models.AlchemicalBase) -> bool:
        """Deletes a mapped object from this model.
        
        If `mapped_object` exists in this model, removes it from
        `session()` and then from this model, and returns `True`.

        Otherwise, returns `False`.
        """

        row = self.rowOf(mapped_object)

        if row == -1:
            return False

        self._session.delete(mapped_object)
        super().removeRecord(row)

        return True

    ################################################################################
    # Overriden methods
    ################################################################################
    def select(self, session: sa_orm.Session) -> None:
        """Reimplements `AlchemicalQueryModel.select()`."""

        super().select(session)
        self._session = session

    def setStatement(self, statement) -> None:
        """Reimplements `AlchemicalQueryModel.setStatement()`."""

        pass

    def createColumns(self, result: sa.engine.Result) -> typing.List[str]:
        """Reimplements `AlchemicalQueryModel.processResultColumns()`."""

        return self.mappedClass().columnNames()

    def record(self, row: int) -> tuple:
        """Reimplements `AlchemicalQueryModel.record()`."""

        instance = self.mappedObject(row)

        return tuple(instance.columnDict().values())

    def appendRecord(self, record: tuple) -> None:
        """Reimplements `AlchemicalQueryModel.appendRecord()`."""

        pass

    def removeRecord(self, row: int) -> tuple:
        """Reimplements `AlchemicalQueryModel.removeRecord()`."""

        pass