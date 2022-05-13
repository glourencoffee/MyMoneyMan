import sqlalchemy.orm as sa_orm
import typing
from PyQt5      import QtCore, QtWidgets
from mymoneyman import models

class AssetCombo(QtWidgets.QWidget):
    """Implements a `QComboBox` that shows a list of `Asset`.

    The class `AssetCombo` allows a user to select an asset from a list of assets,
    which may be provided by calling any of the methods `addAsset()`, `addAssets()`,
    `addCurrencies()`, and `addSecurities()`.

    The methods `addAsset()` and `addAssets()` gives the user more control over
    which assets are stored into the underlying combo, whereas the methods
    `addCurrencies()` and `addSecurities()` retrieve all currencies or securities,
    respectively, associated with a SQLAlchemy session.

    Scoped assets have their scope and code separated by a semicolon (:) as their
    visible text, whereas non-scoped assets only have their code as their visible
    text. Here's an example of what assets stored in this widget may look like:
    - USD
    - EUR
    - NASDAQ:AAPL
    - NASDAQ:GOOG

    Note that although this class may be populated after different models, it always
    uses a `QStandardItemModel` behind the scenes. This allows `addCurrencies()` and
    `addSecurities()` to be combined to populate an instance of this class with all
    assets in the database, but it also means that a change to the database requires
    repopulating the underlying `QStandardItemModel` of that instance.

    See Also
    --------
    `Asset`
    """

    currentAssetChanged = QtCore.pyqtSignal(models.Asset)
    """Emitted if an asset is changed."""

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super(AssetCombo, self).__init__(parent=parent)

        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        self._combo = QtWidgets.QComboBox()
        self._combo.setDuplicatesEnabled(False)
        self._combo.currentIndexChanged.connect(self._onCurrentIndexChanged)

    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._combo)
        main_layout.setContentsMargins(QtCore.QMargins())
    
        self.setLayout(main_layout)

    def clear(self):
        """Removes all items from this widget's underlying model."""

        self._combo.clear()

    def addAsset(self, asset: models.Asset, scope_sep: str = ':'):
        """Adds `asset` to this widget's underlying model.
        
        If `asset.code` already exists in the underlying model, does nothing.
        """

        self._combo.addItem(asset.scopedCode(scope_sep), asset)

    def addAssets(self, assets: typing.Iterable[models.Asset]):
        """Calls `addAsset()` for each asset in an iterable."""

        for asset in assets:
            self.addAsset(asset)

    def addCurrencies(self, session: sa_orm.Session):
        """Adds all currencies in `session`."""

        model = models.CurrencyTableModel()
        model.select(session)

        for currency in model.currencies():
            self.addAsset(currency)

    def addSecurities(self, session: sa_orm.Session, scope_sep: str = ':'):
        """Adds all securities in `session`."""

        model = models.SecurityTableModel()
        model.select(session)

        for security in model.securities():
            self.addAsset(security, scope_sep)

    def count(self) -> int:
        """Returns how many items this widget's underlying model contains."""

        return self._combo.count()

    def asset(self, index: int) -> typing.Optional[models.Asset]:
        """Returns the asset at `index`, or `None` if `index` is invalid."""

        return self._combo.currentData()

    def setCurrentAsset(self, asset: typing.Optional[models.Asset]):
        """Sets `asset` to be currently selected asset if `asset` is not `None`,
        or the invalid index if `asset` is `None`."""

        if asset is None:
            index = -1
        else:
            index = self._combo.findData(asset)

        self._combo.setCurrentIndex(index)

    def currentAsset(self) -> typing.Optional[models.Asset]:
        """Returns the currently selected asset in this widget,
        or `None` if an invalid index is currently selected."""

        return self._combo.currentData()

    ################################################################################
    # Internals
    ################################################################################
    @QtCore.pyqtSlot(int)
    def _onCurrentIndexChanged(self, index: int):
        asset = self.asset(index)
        
        if asset is not None:
            self.currentAssetChanged.emit(asset)