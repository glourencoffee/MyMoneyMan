import typing
from PyQt5      import QtCore, QtGui, QtWidgets
from mymoneyman import models

# TODO: maybe move this to module `utils`? or create a class `CaseLineEdit`?
def _setUpper(line_edit: QtWidgets.QLineEdit, text: str) -> str:
    pos = line_edit.cursorPosition()
    uc_text = text.upper()

    line_edit.setText(uc_text)
    line_edit.setCursorPosition(pos)

    return uc_text

class SecurityEditDialog(QtWidgets.QDialog):
    def __init__(self, model: models.SecurityTreeModel, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._model = model

        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        self.setWindowTitle('Security Edit')

        alnum_validator = QtGui.QRegExpValidator(QtCore.QRegExp('^[a-zA-Z0-9]*$'))

        self._name_lbl = QtWidgets.QLabel('Name')
        self._name_edit = QtWidgets.QLineEdit()
        self._name_edit.setPlaceholderText('Apple, Microsoft, Google...')
        self._name_edit.textEdited.connect(self._onNameTextEdited)

        self._mic_lbl = QtWidgets.QLabel('Market')
        self._mic_combo = QtWidgets.QComboBox()
        self._mic_combo.addItems(self._model.marketCodes())
        self._mic_combo.setEditable(True)
        self._mic_combo.setValidator(alnum_validator)
        self._mic_combo.lineEdit().textEdited.connect(self._onMICComboTextEdited)

        self._code_lbl = QtWidgets.QLabel('Code')
        self._code_edit = QtWidgets.QLineEdit()
        self._code_edit.setPlaceholderText('APPL, MSFT, GOOG...')
        self._code_edit.setValidator(alnum_validator)
        self._code_edit.textEdited.connect(self._onCodeTextEdited)

        self._isin_lbl = QtWidgets.QLabel('ISIN')
        self._isin_edit = QtWidgets.QLineEdit()
        self._isin_edit.setValidator(alnum_validator)
        self._isin_edit.textEdited.connect(self._onISINTextEdited)

        self._type_lbl = QtWidgets.QLabel('Type')
        self._type_combo = QtWidgets.QComboBox()

        for t in models.SecurityType:
            self._type_combo.addItem(t.name, t)

        self._currency_lbl = QtWidgets.QLabel('Currency')
        self._currency_combo = QtWidgets.QComboBox()
        self._currency_combo.setModel(models.CurrencyTableModel())
        self._currency_combo.model().select()
        self._currency_combo.setCurrentIndex(0)

        self._confirm_btn = QtWidgets.QPushButton('Confirm')
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.clicked.connect(self._onConfirmButtonClicked)
    
    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._name_lbl)
        main_layout.addWidget(self._name_edit)
        main_layout.addWidget(self._mic_lbl)
        main_layout.addWidget(self._mic_combo)
        main_layout.addWidget(self._code_lbl)
        main_layout.addWidget(self._code_edit)
        main_layout.addWidget(self._isin_lbl)
        main_layout.addWidget(self._isin_edit)
        main_layout.addWidget(self._type_lbl)
        main_layout.addWidget(self._type_combo)
        main_layout.addWidget(self._currency_lbl)
        main_layout.addWidget(self._currency_combo)
        main_layout.addWidget(self._confirm_btn)
        main_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
    
        self.setLayout(main_layout)

    def marketCode(self) -> str:
        return self._mic_combo.currentText()

    def securityCode(self) -> str:
        return self._code_edit.text()

    def securityName(self) -> str:
        return self._name_edit.text()

    def securityISIN(self) -> typing.Optional[str]:
        return self._isin_edit.text() or None

    def securityType(self) -> models.SecurityType:
        return self._type_combo.currentData()

    def currentyCode(self) -> str:
        return self._currency_combo.currentText()

    def _toggleConfirmButton(self, name: str, mic: str, code: str):
        self._confirm_btn.setEnabled(name != '' and mic != '' and code != '')

    @QtCore.pyqtSlot(str)
    def _onNameTextEdited(self, text: str):
        self._toggleConfirmButton(text, self.marketCode(), self.securityCode())

    @QtCore.pyqtSlot(str)
    def _onCodeTextEdited(self, text: str):
        code = _setUpper(self._code_edit, text)

        self._toggleConfirmButton(self.securityName(), self.marketCode(), code)

    @QtCore.pyqtSlot(str)
    def _onMICComboTextEdited(self, text: str):
        mic = _setUpper(self._mic_combo.lineEdit(), text)

        self._toggleConfirmButton(self.securityName(), mic, self.securityCode())

    @QtCore.pyqtSlot(str)
    def _onISINTextEdited(self, text: str):
        _setUpper(self._isin_edit, text)

    @QtCore.pyqtSlot()
    def _onConfirmButtonClicked(self):
        mic           = self.marketCode()
        code          = self.securityCode()
        name          = self.securityName()
        isin          = self.securityISIN()
        type          = self.securityType()
        currency_code = self.currentyCode()

        if self._model.exists(mic, code):
            QtWidgets.QMessageBox.information(
                self,
                'Security Exists',
                f"The security code '{code}' for the market '{mic}' already exists in the database!"
            )

            return

        if self._model.insert(mic, code, name, isin, type, currency_code):
            self.accept()
        else:
            self.reject()