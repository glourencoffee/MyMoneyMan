import decimal
import typing
from PyQt5 import QtCore, QtWidgets

class SpinBoxDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)
    
    def createEditor(self,
                     parent: QtWidgets.QWidget,
                     option: QtWidgets.QStyleOptionViewItem,
                     index: QtCore.QModelIndex
    ):
        editor = QtWidgets.QDoubleSpinBox(parent)
        editor.setPrefix(editor.locale().currencySymbol() + ' ')
        editor.setMinimum(float('-inf'))
        editor.setMaximum(float('inf'))
        editor.setButtonSymbols(QtWidgets.QDoubleSpinBox.ButtonSymbols.NoButtons)
        editor.setGroupSeparatorShown(True)

        self.setEditorData(editor, index)
        
        return editor
    
    def setEditorData(self, editor: QtWidgets.QDoubleSpinBox, index: QtCore.QModelIndex):
        value = index.model().data(index, QtCore.Qt.ItemDataRole.EditRole)

        if value is None:
            value = 0

        editor.setValue(float(value))

    def setModelData(self, editor: QtWidgets.QDoubleSpinBox, model: QtCore.QAbstractItemModel, index: QtCore.QModelIndex):
        value = decimal.Decimal(editor.value())

        model.setData(index, value, QtCore.Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self,
                             editor: QtWidgets.QWidget,
                             option: QtWidgets.QStyleOptionViewItem,
                             index: QtCore.QModelIndex
    ):
        editor.setGeometry(option.rect)