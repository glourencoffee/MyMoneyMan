import typing
from PyQt5      import QtCore, QtGui, QtWidgets
from mymoneyman import models, widgets

class SecurityEditDialog(QtWidgets.QDialog):
    def __init__(self, model: models.SecurityTableModel, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

        self._model = model

        self._initWidgets()
        self._initLayouts()
        self._initSecurity()

    def _initWidgets(self):
        self.setWindowTitle('Security Edit')

        alnum_validator = QtGui.QRegExpValidator(QtCore.QRegExp('^[a-zA-Z0-9]*$'))

        self._name_lbl = QtWidgets.QLabel('Name')
        self._name_edit = QtWidgets.QLineEdit()
        self._name_edit.setPlaceholderText('Apple, Microsoft, Google...')
        self._name_edit.setMaxLength(models.Security.name.type.length)
        self._name_edit.textEdited.connect(self._onSecurityNameEdited)

        self._market_lbl = QtWidgets.QLabel('Market')
        self._market_combo = QtWidgets.QComboBox()
        self._market_combo.addItems(sorted(self._model.markets()))
        self._market_combo.setEditable(True)
        self._market_combo.setValidator(alnum_validator)
        self._market_combo.setLineEdit(widgets.CaseLineEdit(widgets.CaseLineEdit.Case.Upper))
        self._market_combo.lineEdit().setMaxLength(models.Security.market.type.length)
        self._market_combo.lineEdit().textEdited.connect(self._onMarketComboTextEdited)

        self._code_lbl = QtWidgets.QLabel('Code')
        self._code_edit = widgets.CaseLineEdit(widgets.CaseLineEdit.Case.Upper)
        self._code_edit.setPlaceholderText('AAPL, MSFT, GOOG...')
        self._code_edit.setValidator(alnum_validator)
        self._code_edit.textEdited.connect(self._onSecurityCodeEdited)
        self._code_edit.setMaxLength(models.Security.code.type.length)

        self._isin_lbl = QtWidgets.QLabel('ISIN')
        self._isin_edit = widgets.CaseLineEdit(widgets.CaseLineEdit.Case.Upper)
        self._isin_edit.setValidator(alnum_validator)
        self._isin_edit.setMaxLength(models.Security.isin.type.length)
        self._isin_edit.textEdited.connect(self._onISINEdited)

        self._type_lbl = QtWidgets.QLabel('Type')
        self._type_combo = QtWidgets.QComboBox()

        # TODO: turn this combo into its own widget class?
        for t in models.SecurityType:
            self._type_combo.addItem(t.name, t)

        self._type_combo.currentIndexChanged.connect(self._onSecurityTypeIndexChanged)

        self._currency_lbl = QtWidgets.QLabel('Currency')
        self._currency_combo = widgets.AssetCombo()
        self._currency_combo.addCurrencies(self._model.session())
        self._currency_combo.currentAssetChanged.connect(self._onCurrencyAssetChanged)

        self._precision_lbl = QtWidgets.QLabel('Precision')
        self._precision_spin = QtWidgets.QSpinBox()
        self._precision_spin.setRange(0, 18)
        self._precision_spin.setValue(0)
        self._precision_spin.valueChanged.connect(self._onPrecisionValueChanged)

        self._confirm_btn = QtWidgets.QPushButton('Confirm')
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.clicked.connect(self.accept)
    
    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._name_lbl)
        main_layout.addWidget(self._name_edit)
        main_layout.addWidget(self._market_lbl)
        main_layout.addWidget(self._market_combo)
        main_layout.addWidget(self._code_lbl)
        main_layout.addWidget(self._code_edit)
        main_layout.addWidget(self._isin_lbl)
        main_layout.addWidget(self._isin_edit)
        main_layout.addWidget(self._type_lbl)
        main_layout.addWidget(self._type_combo)
        main_layout.addWidget(self._currency_lbl)
        main_layout.addWidget(self._currency_combo)
        main_layout.addWidget(self._precision_lbl)
        main_layout.addWidget(self._precision_spin)
        main_layout.addWidget(self._confirm_btn)
        main_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
    
        self.setLayout(main_layout)

    def _initSecurity(self):
        self._security = models.Security(
            market        = self._market_combo.currentText(),
            code          = self._code_edit.text(),
            name          = self._name_edit.text(),
            currency      = self._currency_combo.currentAsset(),
            precision     = self._precision_spin.value(),
            security_type = self._type_combo.currentData(),
            isin          = self._isin_edit.text() or None
        )

    def security(self):
        return self._security

    ################################################################################
    # Overriden methods
    ################################################################################
    def accept(self):
        self._model.upsert(self._security)

        super().accept()

    ################################################################################
    # Internals
    ################################################################################
    def _toggleConfirmButton(self):
        market = self._market_combo.currentText()
        name   = self._name_edit.text()
        code   = self._code_edit.text()

        if market == '' or name == '' or code == '':
            self._confirm_btn.setEnabled(False)
        else:
            self._confirm_btn.setEnabled(not self._model.existsWithCode(market, code))

    @QtCore.pyqtSlot(str)
    def _onSecurityNameEdited(self, text: str):
        self._security.name = text

        self._toggleConfirmButton()

    @QtCore.pyqtSlot(str)
    def _onMarketComboTextEdited(self, text: str):
        self._security.market = text

        self._toggleConfirmButton()

    @QtCore.pyqtSlot(str)
    def _onSecurityCodeEdited(self, text: str):
        self._security.code = text

        self._toggleConfirmButton()

    @QtCore.pyqtSlot(str)
    def _onISINEdited(self, text: str):
        self._security.isin = text

    @QtCore.pyqtSlot(int)
    def _onSecurityTypeIndexChanged(self, index: int):
        self._security.security_type = self._type_combo.itemData(index)

    @QtCore.pyqtSlot(models.Asset)
    def _onCurrencyAssetChanged(self, asset: models.Asset):
        assert isinstance(asset, models.Currency)

        self._security.currency = asset

    @QtCore.pyqtSlot(int)
    def _onPrecisionValueChanged(self, value: int):
        self._security.precision = value