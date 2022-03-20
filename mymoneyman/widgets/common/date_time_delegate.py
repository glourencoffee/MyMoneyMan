import typing
from PyQt5 import QtCore, QtWidgets

class DateTimeDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, datetime_format: str, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)

        self._datetime_format = datetime_format
    
    def createEditor(self,
                     parent: QtWidgets.QWidget,
                     option: QtWidgets.QStyleOptionViewItem,
                     index: QtCore.QModelIndex
    ):
        editor = QtWidgets.QDateTimeEdit(parent)
        editor.setCalendarPopup(True)
        editor.setDisplayFormat(self._datetime_format)
        self.setDateTimeFromIndex(editor, index)
        
        return editor
    
    def setEditorData(self, editor: QtWidgets.QWidget, index: QtCore.QModelIndex):
        self.setDateTimeFromIndex(editor, index)

    def setDateTimeFromIndex(self, editor: QtWidgets.QDateTimeEdit, index: QtCore.QModelIndex):
        datetime = index.model().data(index, QtCore.Qt.ItemDataRole.EditRole)

        editor: QtWidgets.QDateTimeEdit = editor
        editor.setDateTime(datetime)

    def setModelData(self, editor: QtWidgets.QWidget, model: QtCore.QAbstractItemModel, index: QtCore.QModelIndex):
        editor: QtWidgets.QDateTimeEdit = editor
        editor.interpretText()

        datetime = editor.dateTime()
        model.setData(index, datetime.toString(self._datetime_format), QtCore.Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self,
                             editor: QtWidgets.QWidget,
                             option: QtWidgets.QStyleOptionViewItem,
                             index: QtCore.QModelIndex
    ):
        editor: QtWidgets.QDateTimeEdit = editor
        editor.setGeometry(option.rect)