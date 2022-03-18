import collections
import decimal
import enum
import typing
from PyQt5              import QtCore, QtGui, QtWidgets
from mymoneyman.widgets import accounts as widgets
from mymoneyman         import models

_GroupComboData = collections.namedtuple('_GroupComboData', ['account_group', 'account_type'])

class AccountEditDialog(QtWidgets.QDialog):
    class EditionMode(enum.IntEnum):
        Creation = 0
        Edition  = 1

    def __init__(self, mode: EditionMode, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._mode = mode
        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        #TODO: tr()
        self.setWindowTitle(f'Account {self._mode.name} Window')

        self._name_lbl = QtWidgets.QLabel('Name')
        self._name_edit = QtWidgets.QLineEdit()

        self._desc_lbl = QtWidgets.QLabel('Description')
        self._desc_edit = QtWidgets.QLineEdit()

        self._currency_lbl = QtWidgets.QLabel('Currency')
        self._currency_combo = QtWidgets.QComboBox()
        self._currency_combo.addItems(('USD', 'BRL', 'TRY', 'EUR'))

        if self._mode == AccountEditDialog.EditionMode.Edition:
            # TODO: check if there are any transactions for account, in which case, disable change of currency.
            self._currency_combo.setEnabled(False)

        self._type_lbl   = QtWidgets.QLabel('Type')
        self._type_combo = QtWidgets.QComboBox()

        for acc_type in models.AccountType:
            # TODO: tr()
            if acc_type == models.AccountType.Equity:
                continue

            acc_name  = acc_type.name if acc_type != models.AccountType.CreditCard else 'Credit Card'
            acc_group = models.AccountGroup.fromAccountType(acc_type)
            
            # TODO: icon
            self._type_combo.addItem(QtGui.QIcon(), acc_name, _GroupComboData(acc_group, acc_type))

        self._type_combo.currentIndexChanged.connect(self._onGroupCurrentIndexChanged)
        self._previous_group_data = self._currentGroupData()

        self._parent_lbl  = QtWidgets.QLabel('Enclosed by')
        self._parent_tree = widgets.AccountTreeWidget()
        self._parent_tree.setHeaderHidden(True)
        self._parent_tree.model().select([self._currentGroupData().account_group])

        if self._mode == AccountEditDialog.EditionMode.Creation:
            self._opening_balance_lbl       = QtWidgets.QLabel('Opening balance')
            self._opening_balance_edit      = QtWidgets.QLineEdit()
            self._opening_balance_date_lbl  = QtWidgets.QLabel('Date')
            self._opening_balance_date_edit = QtWidgets.QDateTimeEdit()

        self._confirm_btn = QtWidgets.QPushButton('Confirm')
        self._confirm_btn.clicked.connect(self._onConfirmButtonClicked)

    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._name_lbl)
        main_layout.addWidget(self._name_edit)
        main_layout.addWidget(self._desc_lbl)
        main_layout.addWidget(self._desc_edit)
        main_layout.addWidget(self._currency_lbl)
        main_layout.addWidget(self._currency_combo)
        main_layout.addWidget(self._type_lbl)
        main_layout.addWidget(self._type_combo)
        main_layout.addWidget(self._parent_lbl)
        main_layout.addWidget(self._parent_tree)

        if self._mode == AccountEditDialog.EditionMode.Creation:
            opening_balance_layout = QtWidgets.QGridLayout()
            opening_balance_layout.addWidget(self._opening_balance_lbl,       0, 0)
            opening_balance_layout.addWidget(self._opening_balance_edit,      1, 0)
            opening_balance_layout.addWidget(self._opening_balance_date_lbl,  0, 1)
            opening_balance_layout.addWidget(self._opening_balance_date_edit, 1, 1)

            main_layout.addLayout(opening_balance_layout)

        main_layout.addWidget(self._confirm_btn)
        main_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        self.setLayout(main_layout)

    def setType(self, text: str):
        self._type_combo.setCurrentText(text)
    
    def setName(self, text: str):
        self._name_edit.setText(text)

    def setDescription(self, text: str):
        self._desc_edit.setText(text)

    def accountType(self) -> models.AccountType:
        return self._currentGroupData().account_type
    
    def accountName(self) -> str:
        return self._name_edit.text()

    def accountDescription(self) -> str:
        return self._desc_edit.text()

    def _currentGroupData(self) -> _GroupComboData:
        return self._type_combo.currentData()

    @QtCore.pyqtSlot(int)
    def _onGroupCurrentIndexChanged(self, _: int):
        current_data = self._currentGroupData()

        if current_data.account_group != self._previous_group_data.account_group:
            self._parent_tree.model().select([current_data.account_group])
            self._previous_group_data = current_data

    @QtCore.pyqtSlot()
    def _onConfirmButtonClicked(self):
        account_type = self.accountType()
        account_name = self.accountName()
        account_desc = self.accountDescription()
        parent_item  = self._parent_tree.currentItem()
        parent_id    = parent_item.id() if parent_item is not None else None

        model       = self._parent_tree.model()
        is_creation = self._mode == AccountEditDialog.EditionMode.Creation

        if is_creation:
            account_exists = model.hasAccount(account_name, account_type, parent_id)

            if account_exists:
                # TODO: tr()
                if parent_item is None:
                    account_group = models.AccountGroup.fromAccountType(account_type)
                    description = f"Top-level account '{account_name}' for group '{account_group.name.title()}' already exists."
                else:
                    description = f"There is already an account named '{account_name}' under parent '{parent_item.name()}'."

                QtWidgets.QMessageBox.information(self, 'Account exists', description)
            else:
                print('insert account (name:', account_name, 'type:', account_type, 'parent id:', parent_id, ')')

                if model.addAccount(account_name, account_type, account_desc, parent_id):
                    self.accept()
                else:
                    print('rejecting...')
                    self.reject()
        else:
            # TODO
            pass