import enum
import typing
from PyQt5      import QtCore, QtGui, QtWidgets
from mymoneyman import models

def makeSecurityStandardItemModel(mic: typing.Optional[str] = None, prefix_mic: bool = True) -> QtGui.QStandardItemModel:
    tree_model = models.SecurityTreeModel()
    tree_model.select(mic)

    std_model = QtGui.QStandardItemModel()

    for top_level_item in tree_model.topLevelItems():
        prefix = (top_level_item.mic() + ':') if prefix_mic else ''
        
        for child in top_level_item.children():
            std_item = QtGui.QStandardItem(prefix + child.code())
            std_item.setData(child.id())

            std_model.appendRow(std_item)

    return std_model

class AssetCombo(QtWidgets.QWidget):
    class AssetType(enum.IntEnum):
        Security = 0
        Currency = 1

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._asset_type = None

        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        self._combo = QtWidgets.QComboBox()
        self.setAssetType(AssetCombo.AssetType.Currency)
    
    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._combo)
        main_layout.setContentsMargins(QtCore.QMargins())
    
        self.setLayout(main_layout)

    def setAssetType(self, asset_type: AssetType):
        if self._asset_type == asset_type:
            return

        if asset_type == AssetCombo.AssetType.Currency:
            model = models.CurrencyTableModel()
            model.select()

            self._combo.setModel(model)
        else:
            self._combo.setModel(makeSecurityStandardItemModel())

        self._asset_type = asset_type

    def assetType(self) -> AssetType:
        return self._asset_type

    def setCurrentIndex(self, index: int):
        self._combo.setCurrentIndex(index)

    def currentIndex(self) -> int:
        return self._combo.currentIndex()

    def currentAssetId(self) -> typing.Optional[int]:
        row = self._combo.currentIndex()

        if row < 0:
            return None

        if self._asset_type == AssetCombo.AssetType.Currency:
            model: models.CurrencyTableModel = self._combo.model()
            index = model.index(row, 0)
            
            item = model.itemFromIndex(index)

            return item.id()
        else:
            model: QtGui.QStandardItemModel = self._combo.model()
            index = model.index(row, 0)

            item = model.itemFromIndex(index)

            return item.data()