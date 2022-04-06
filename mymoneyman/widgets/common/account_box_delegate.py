import typing
from PyQt5              import QtCore, QtWidgets
from mymoneyman         import models
from mymoneyman.widgets import common

class AccountBoxDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, model: models.AccountListModel = models.AccountListModel(), parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)

        self._model = model
        self._model.select()
    
    def createEditor(self,
                     parent: QtWidgets.QWidget,
                     option: QtWidgets.QStyleOptionViewItem,
                     index: QtCore.QModelIndex
    ):
        editor = common.AccountBox(self._model, parent)
        editor.setEditable(True)
        
        self.setEditorData(editor, index)
        
        return editor
    
    def setEditorData(self, editor: common.AccountBox, index: QtCore.QModelIndex):
        account_id = index.model().data(index, QtCore.Qt.ItemDataRole.EditRole)

        editor.setCurrentAccount(account_id)

    def setModelData(self, editor: common.AccountBox, model: QtCore.QAbstractItemModel, index: QtCore.QModelIndex):
        account = editor.currentAccount()

        if account is None:
            account_id   = None
            account_name = None
        else:
            account_id   = account.id
            account_name = account.name
        
        model.setData(index, account_id,   QtCore.Qt.ItemDataRole.EditRole)
        model.setData(index, account_name, QtCore.Qt.ItemDataRole.DisplayRole)

    def updateEditorGeometry(self,
                             editor: common.AccountBox,
                             option: QtWidgets.QStyleOptionViewItem,
                             index: QtCore.QModelIndex
    ):
        editor.setGeometry(option.rect)