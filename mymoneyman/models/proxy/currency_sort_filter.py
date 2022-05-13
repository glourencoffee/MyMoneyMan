import enum
import typing
from PyQt5      import QtCore
from mymoneyman import models

class CurrencySortFilterProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

        self._accepts_fiat   = True
        self._accepts_crypto = True

    def setCurrencyModel(self, model: models.CurrencyTableModel):
        super().setSourceModel(model)

    def currencyModel(self) -> models.CurrencyTableModel:
        return self.sourceModel()

    def setAccepted(self, fiat: bool, crypto: bool):
        if self._accepts_fiat == fiat and self._accepts_crypto == crypto:
            return
        
        self._accepts_fiat   = fiat
        self._accepts_crypto = crypto
        self.invalidateFilter()

    def setAllAccepted(self):
        self.setAccepted(fiat=True, crypto=True)

    def setNoneAccepted(self):
        self.setAccepted(fiat=False, crypto=False)

    def setFiatOnly(self):
        self.setAccepted(fiat=True, crypto=False)
    
    def setCryptoOnly(self):
        self.setAccepted(fiat=False, crypto=True)

    def filterAcceptsFiat(self) -> bool:
        return self._accepts_fiat
    
    def filterAcceptsCrypto(self) -> bool:
        return self._accepts_crypto
    
    ################################################################################
    # Overriden methods
    ################################################################################
    def setSourceModel(self, source_model: QtCore.QAbstractItemModel):
        if not isinstance(source_model, models.CurrencyModel):
            raise TypeError('source model is not instance of CurrencyModel')

        self.setCurrencyModel(source_model)

    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:
        source_model = self.currencyModel()
        currency     = source_model.currency(source_row)

        if currency.is_fiat:
            return self.filterAcceptsFiat()
        else:
            return self.filterAcceptsCrypto()

    def currency(self, row: int) -> models.Currency:
        proxy_index  = self.index(row, 0)
        source_index = self.mapToSource(proxy_index)
        source_model = self.currencyModel()

        return source_model.currency(source_index.row())