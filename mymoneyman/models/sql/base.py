from __future__ import annotations
import typing
import sqlalchemy     as sa
import sqlalchemy.orm as sa_orm
from mymoneyman import utils

Base = sa_orm.declarative_base()

class AlchemicalBase(Base):
    """Abstracts all SQLAlchemy mapped classes."""

    __abstract__ = True

    @classmethod
    def columns(cls) -> typing.Iterable[sa.Column]:
        """Returns all columns in this mapped class."""

        return (column for column in sa.inspect(cls).c)

    @classmethod
    def columnNames(cls) -> typing.List[str]:
        """Returns the name of all columns in this mapped class."""

        names = []

        for column in cls.columns():
            # Polymorphism may result in repeated column names.
            # Ensure `names` have no duplicates.
            if column.name not in names:
                names.append(column.name)

        return names

    def attributes(self, changed: bool = False) -> typing.Iterable[sa_orm.AttributeState]:
        """Returns attributes of this mapped object.
        
        If `changed` is `False`, returns the name of all attributes of this
        mapped object. Otherwise, returns only the attributes of this mapped
        object that have changed.

        Note that an object's attributes may include more than the columns
        defined by that object's class. For example, this method will return
        any `sa.relationship()` definitions. To return only columns of a
        mapped object, call `columns()`.
        """

        state: sa_orm.InstanceState = sa.inspect(self)

        return (
            attr
            for attr in state.attrs
            if not changed or state.get_history(attr.key, False).has_changes()
        )

    def attributeNames(self, changed: bool = False) -> typing.List[str]:
        """Returns the names of attributes of this mapped object."""

        names = []

        for attr in self.attributes(changed):
            # Polymorphism may result in repeated column names.
            # Ensure `names` have no duplicates.
            if attr.key not in names:
                names.append(attr.key)

        return names

    def attributeDict(self, changed: bool = False) -> typing.Dict[str, typing.Any]:
        """Returns a dict of attribute names and values.

        The returned dict in the same order as `attributeNames()`.

        >>> class Employee(AlchemicalBase):
        ...     id   = sa.Column(...)
        ...     name = sa.Column(...)
        ...     boss = sa.relationship(...)
        ... \n
        >>> Employee.attributeNames()
        ['id', 'name', 'boss']
        >>> Employee(id=1, name='John Doe', boss=...).attributeDict()
        {'id': 1, name: 'John Doe', boss: ...}
        """

        return {attr.key: getattr(self, attr.key) for attr in self.attributes(changed)}

    def hasChanged(self, attr_name: typing.Optional[str] = None) -> bool:
        """Returns whether an attribute of this model has changed.
        
        If `attr_name` is `None`, returns `True` if any attribute of this
        mapped object has changed.

        If `attr_name` is not `None`, returns `True` if this mapped object
        has an attribute whose name is `attr_name` and such attribute has
        changed.

        Otherwise, returns `False`.
        """

        state: sa_orm.InstanceState = sa.inspect(self)

        for attr in state.attrs:
            if attr_name is not None and attr.key != attr_name:
                continue
                
            if state.get_history(attr.key, False).has_changes():
                return True

        return False

    def columnDict(self) -> typing.Dict[str, typing.Any]:
        """Returns a dict of column names and values of this mapped object.
        
        The returned dict in the same order as `columnNames()`.

        >>> class Employee(AlchemicalBase):
        ...     id   = sa.Column(sa.Integer, primary_key=True)
        ...     name = sa.Column(sa.String)
        ... \n
        >>> Employee.columnNames()
        ['id', 'name']
        >>> Employee(id=1, name='John Doe').columnDict()
        {'id': 1, 'name': 'John Doe'}
        """

        return {column: getattr(self, column) for column in self.columnNames()}

    def session(self) -> typing.Optional[sa_orm.Session]:
        """Returns the SQLAlchemy session which this mapped object
        is attached to, or `None` if this mapped object is detached."""

        return sa_orm.object_session(self)

    def hasSession(self) -> bool:
        """Returns whether this mapped object is attached to a session.
        
        Effectively returns whether `session()` is not `None`.
        """

        return self.session() is not None

    def refresh(self):
        """Refreshes this mapped object to its state as in the database.
        
        Calling this method has no effect if `hasSession()` is `False`.
        """

        session = self.session()

        if session is not None:
            session.refresh(self)

    def __repr__(self) -> str:
        return utils.makeRepr(self.__class__, self.columnDict())