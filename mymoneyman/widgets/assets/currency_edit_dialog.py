import typing
from PyQt5      import QtCore, QtGui, QtWidgets
from mymoneyman import models

class CurrencyEditDialog(QtWidgets.QDialog):
    def __init__(self, model: models.CurrencyTableModel, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._model = model

        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        self.setWindowTitle('Currency Edit')

        self._name_lbl = QtWidgets.QLabel('Name')
        self._name_edit = QtWidgets.QLineEdit()

        alnum_validator = QtGui.QRegExpValidator(QtCore.QRegExp('^[a-zA-Z0-9_]*$'))

        self._code_lbl = QtWidgets.QLabel('Code')
        self._code_edit = QtWidgets.QLineEdit()
        self._code_edit.setValidator(alnum_validator)
        self._code_edit.setMaxLength(8)
        self._code_edit.textEdited.connect(self._onCodeTextEdited)

        self._symbol_lbl = QtWidgets.QLabel('Symbol')
        self._symbol_edit = QtWidgets.QLineEdit()
        self._symbol_edit.setMaxLength(5)

        self._precision_lbl = QtWidgets.QLabel('Precision')
        self._precision_spin = QtWidgets.QSpinBox()
        self._precision_spin.setRange(0, 18)
        self._precision_spin.setValue(2)

        self._fiat_chk = QtWidgets.QCheckBox('Is Fiat')
        self._fiat_chk.setChecked(True)

        self._confirm_btn = QtWidgets.QPushButton('Confirm')
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.clicked.connect(self._onConfirmButtonClicked)
    
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

    @QtCore.pyqtSlot(str)
    def _onCodeTextEdited(self, text: str):
        if text == '':
            self._confirm_btn.setEnabled(False)
        else:
            self._confirm_btn.setEnabled(not self._model.exists(text))

    @QtCore.pyqtSlot()
    def _onConfirmButtonClicked(self):
        code      = self._code_edit.text()
        name      = self._name_edit.text()
        symbol    = self._symbol_edit.text()
        precision = self._precision_spin.value()
        is_fiat   = self._fiat_chk.isChecked()

        if self._model.insert(code, name, symbol, precision, is_fiat):
            self.accept()
        else:
            self.reject()