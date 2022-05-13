import typing
from PyQt5        import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from mymoneyman   import models, widgets, utils

class AccountComboDelegate(QtWidgets.QStyledItemDelegate):
    """Allows selecting an account through a combo box for a model.

    The class `AccountComboDelegate` implements a `QStyledItemDelegate` to
    creates an editable `AccountCombo` editor when active.
    
    The model which this class is used with is expected to provide and receive
    instances of `Account` on its implementation of the methods `QAbstractItemModel.data()`
    and `QAbstractItemModel.setData()` for the role `Qt.ItemDataRole.EditRole`.

    >>> model = AccountTableModel()
    >>> model.select(session)
    >>> model.data(model.index(0, 0), Qt.ItemDataRole.EditRole)
    <Account: id=3 name='Wallet' ...>
    >>> delegate = AccountComboDelegate()
    >>> view = QTableView()
    >>> view.setModel(model)
    >>> view.setDelegate(delegate)

    See Also
    --------
    `AccountCombo`
    """

    def __init__(self, model: models.AccountTableModel, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

        self._model = model
    
    def createEditor(self,
                     parent: QtWidgets.QWidget,
                     option: QtWidgets.QStyleOptionViewItem,
                     index: QtCore.QModelIndex
    ):
        editor = widgets.AccountCombo(parent=parent)
        editor.model().setSourceModel(self._model)
        editor.setEditable(True)
        
        self.setEditorData(editor, index)
        
        return editor
    
    def setEditorData(self, editor: widgets.AccountCombo, index: QtCore.QModelIndex):
        model   = index.model()
        account = index.model().data(index, Qt.ItemDataRole.EditRole)

        if account is None or isinstance(account, models.Account):
            editor.setCurrentAccount(account)
        else:
            print(f'data at index {utils.indexLocation(index)} of model {model} for user role is not an instance of Account')

    def setModelData(self, editor: widgets.AccountCombo, model: QtCore.QAbstractItemModel, index: QtCore.QModelIndex):
        account = editor.currentAccount()

        model.setData(index, account, QtCore.Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self,
                             editor: widgets.AccountCombo,
                             option: QtWidgets.QStyleOptionViewItem,
                             index: QtCore.QModelIndex
    ):
        editor.setGeometry(option.rect)