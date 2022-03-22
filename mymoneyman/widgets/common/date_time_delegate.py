import typing
from PyQt5 import QtCore, QtWidgets

class DateTimeDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, display_format: str, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)

        self._display_format = display_format
    
    def createEditor(self,
                     parent: QtWidgets.QWidget,
                     option: QtWidgets.QStyleOptionViewItem,
                     index: QtCore.QModelIndex
    ):
        editor = QtWidgets.QDateTimeEdit(parent)
        editor.setCalendarPopup(True)
        editor.setDisplayFormat(self._display_format)
        
        self.setEditorData(editor, index)
        
        return editor
    
    def setEditorData(self, editor: QtWidgets.QDateTimeEdit, index: QtCore.QModelIndex):
        datetime = index.model().data(index, QtCore.Qt.ItemDataRole.EditRole)

        editor.setDateTime(datetime)

    def setModelData(self, editor: QtWidgets.QDateTimeEdit, model: QtCore.QAbstractItemModel, index: QtCore.QModelIndex):
        editor.interpretText()

        datetime = editor.dateTime()
        model.setData(index, editor.dateTime(), QtCore.Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self,
                             editor: QtWidgets.QDateTimeEdit,
                             option: QtWidgets.QStyleOptionViewItem,
                             index: QtCore.QModelIndex
    ):
        editor.setGeometry(option.rect)