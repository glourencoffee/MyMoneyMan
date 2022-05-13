import typing
from PyQt5      import QtCore, QtGui, QtWidgets
from mymoneyman import models, widgets

class CurrencyEditDialog(QtWidgets.QDialog):
    def __init__(self, model: models.CurrencyTableModel, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

        self._model = model
        
        self._initWidgets()
        self._initLayouts()
        self._initCurrency()

    def _initWidgets(self):
        self.setWindowTitle('Currency Edit')

        self._name_lbl = QtWidgets.QLabel('Name')
        self._name_edit = QtWidgets.QLineEdit()
        self._name_edit.setPlaceholderText('Dollar, Euro, Bitcoin...')
        self._name_edit.setMaxLength(models.Currency.name.type.length)
        self._name_edit.textEdited.connect(self._onNameEdited)

        alnum_validator = QtGui.QRegExpValidator(QtCore.QRegExp('^[a-zA-Z0-9_]*$'))

        self._code_lbl = QtWidgets.QLabel('Code')
        self._code_edit = widgets.CaseLineEdit(widgets.CaseLineEdit.Case.Upper)
        self._code_edit.setPlaceholderText('USD, EUR, BTC...')
        self._code_edit.setValidator(alnum_validator)
        self._code_edit.setMaxLength(models.Currency.code.type.length)
        self._code_edit.textEdited.connect(self._onCodeEdited)

        self._symbol_lbl = QtWidgets.QLabel('Symbol')
        self._symbol_edit = QtWidgets.QLineEdit()
        self._symbol_edit.setPlaceholderText('$, €, ₿...')
        self._symbol_edit.setMaxLength(models.Currency.code.type.length)
        self._symbol_edit.textEdited.connect(self._onSymbolEdited)

        self._precision_lbl = QtWidgets.QLabel('Precision')
        self._precision_spin = QtWidgets.QSpinBox()
        self._precision_spin.setRange(0, 18)
        self._precision_spin.setValue(2)
        self._precision_spin.valueChanged.connect(self._onPrecisionValueChanged)

        self._fiat_chk = QtWidgets.QCheckBox('Is Fiat')
        self._fiat_chk.setChecked(True)
        self._fiat_chk.toggled.connect(self._onFiatToggled)

        self._confirm_btn = QtWidgets.QPushButton('Confirm')
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.clicked.connect(self.accept)
    
    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._name_lbl)
        main_layout.addWidget(self._name_edit)
        main_layout.addWidget(self._code_lbl)
        main_layout.addWidget(self._code_edit)
        main_layout.addWidget(self._symbol_lbl)
        main_layout.addWidget(self._symbol_edit)
        main_layout.addWidget(self._precision_lbl)
        main_layout.addWidget(self._precision_spin)
        main_layout.addWidget(self._fiat_chk)
        main_layout.addWidget(self._confirm_btn)
        main_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
    
        self.setLayout(main_layout)

    def _initCurrency(self):
        self._currency = models.Currency(
            code      = self._code_edit.text(),
            name      = self._name_edit.text(),
            precision = self._precision_spin.value(),
            symbol    = self._symbol_edit.text(),
            is_fiat   = self._fiat_chk.isChecked()
        )

    def accept(self):
        self._model.upsert(self._currency)

        super().accept()

    def _toggleConfirmButton(self):
        code = self._currency.code
        name = self._currency.name

        if code == '' or name == '':
            self._confirm_btn.setEnabled(False)
        else:
            self._confirm_btn.setEnabled(not self._model.existsWithCode(code))

    @QtCore.pyqtSlot(str)
    def _onNameEdited(self, text: str):
        self._currency.name = text

        self._toggleConfirmButton()

    @QtCore.pyqtSlot(str)
    def _onCodeEdited(self, text: str):
        self._currency.code = text

        self._toggleConfirmButton()

    @QtCore.pyqtSlot(str)
    def _onSymbolEdited(self, text: str):
        self._currency.symbol = text

    @QtCore.pyqtSlot(int)
    def _onPrecisionValueChanged(self, value: int):
        self._currency.precision = value

    @QtCore.pyqtSlot(bool)
    def _onFiatToggled(self, checked: bool):
        self._currency.is_fiat = checked