import typing
from PyQt5      import QtCore, QtGui, QtWidgets
from mymoneyman import models, widgets

class AccountEditDialog(QtWidgets.QDialog):
    """
    The class `AccountEditDialog` allows the user to create or modify an account
    by providing widgets related to each attribute of `Account`.
    
    An instance of the model `Account` is stored by this class at all times.
    This instance is default-constructed upon this class's construction, and may
    be changed and retrieved with the methods `setAccount()` and `account()`,
    respectively.

    The `Account` instance associated with this class is changed whenever a value
    of any of the child widgets contained by this class is changed. For example,
    this class has a `QLineEdit` child widget that allows a user to set the name
    of the `Account` instance. Every change to this `QLineEdit.text()` will cause
    the attribute `Account.name` to be changed. Thus, a call to `account()` will
    always reflect the up-to-date state of the `Account` instance.

    The `QDialog` methods `accept()` and `reject()` are overriden by this class to
    persist or refresh the associated `Account`, respectively. By default, a pop-up
    confirmation message is shown upon `reject()` if any attribute of the `Account`
    instance is changed. This behavior may be changed by calling the method
    `setRejectPopupEnabled()`. In any case, irrespective of whether the pop-up
    is enabled or disabled, no pop-up message is ever shown if the `Account` has
    no modified attributes, which includes the act of changing an attribute to a
    different value and then changing it back to its original value. For example,
    if `Account.name` was originally `'A'`, then changed to `'B'`, and then back
    to `'A'`, a pop-up dialog is not shown upon `reject()`. `reject()` will also
    unconditionally disregard the pop-up message if the associated account is a new
    account which is not attached to an ORM session.
    
    An `AccountTreeModel` must be passed in upon construction of this class. This is
    the tree model that will be used to show a tree of parent accounts for the user
    to choose from, and is the model against which persisting operations will be
    applied upon `accept()`. This tree model may be retrieved by calling `model()`.

    See Also
    --------
    `Account`
    """

    def __init__(self, model: models.AccountTableModel, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._model = model
        self._reject_popup_enabled = True

        self._initWidgets()
        self._initLayouts()
        self._initAccount()

    def _initWidgets(self):
        #TODO: tr()
        self.setWindowTitle(f'Account Edit')

        self._name_lbl = QtWidgets.QLabel('Name')
        self._name_edit = QtWidgets.QLineEdit()
        self._name_edit.textEdited.connect(self._onNameEdited)

        self._desc_lbl = QtWidgets.QLabel('Description')
        self._desc_edit = QtWidgets.QLineEdit()
        self._desc_edit.textEdited.connect(self._onDescriptionEdited)

        self._type_lbl   = QtWidgets.QLabel('Type')
        self._type_combo = widgets.AccountTypeCombo()
        self._type_combo.setAccountTypes(t for t in models.AccountType if t != models.AccountType.Equity)
        self._type_combo.currentAccountTypeChanged.connect(self._onCurrentAccountTypeChanged)

        self._confirm_btn = QtWidgets.QPushButton('Confirm')
        self._confirm_btn.clicked.connect(self.accept)

        self._asset_lbl = QtWidgets.QLabel('Currency')
        self._asset_combo = widgets.AssetCombo()
        self._updateAssetCombo(self._type_combo.currentAccountType())
        self._asset_combo.currentAssetChanged.connect(self._onCurrentAssetChanged)
        # TODO: check if there are any transactions for account, in which case, disable change of asset.
        # self._asset_combo.setEnabled(False)

        self._parent_lbl  = QtWidgets.QLabel('Enclosed by')
        self._parent_tree = widgets.AccountTreeWidget()
        self._parent_tree.setHeaderHidden(True)
        self._parent_tree.model().setSourceModel(self._model)
        self._parent_tree.model().setFilterGroup(self._type_combo.currentAccountType().group())
        self._parent_tree.clicked.connect(self._onParentTreeClicked)

        for column in models.AccountTreeProxyModel.Column:
            hide = (column != models.AccountTreeProxyModel.Column.Name)

            self._parent_tree.setColumnHidden(column, hide)

    def _initLayouts(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._name_lbl)
        main_layout.addWidget(self._name_edit)
        main_layout.addWidget(self._desc_lbl)
        main_layout.addWidget(self._desc_edit)
        main_layout.addWidget(self._type_lbl)
        main_layout.addWidget(self._type_combo)
        main_layout.addWidget(self._asset_lbl)
        main_layout.addWidget(self._asset_combo)
        main_layout.addWidget(self._parent_lbl)
        main_layout.addWidget(self._parent_tree)

        main_layout.addWidget(self._confirm_btn)
        main_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        self.setLayout(main_layout)

    def _initAccount(self):
        self._account = models.Account(
            type        = self._type_combo.currentAccountType(),
            name        = self._name_edit.text(),
            description = self._desc_edit.text(),
            asset       = self._asset_combo.currentAsset(),
            parent      = None
        )

    def model(self) -> models.AccountTableModel:
        return self._model

    def setAccount(self, account: models.Account):
        print('setAccount(): account attributes:', account.attributeNames())

        self._name_edit.setText(account.name)
        self._desc_edit.setText(account.description)
        self._type_combo.setCurrentAccountType(account.type)
        self._updateAssetCombo(account.type)

        if account.hasSession():
            self._parent_tree.setAccountHidden(account, True)

        if self._account.hasSession():
            # Account has session, which means it has an id. We may have set it 
            # hidden on the parent tree so that it can't be chosen as a parent,
            # but now that we're setting a different account, it doesn't need to
            # be hidden anymore.

            self._parent_tree.setAccountHidden(self._account, False)

        self._account = account

    def account(self) -> models.Account:
        return self._account

    def setRejectPopupEnabled(self, enabled: bool):
        self._reject_popup_enabled = enabled

    def isRejectPopupEnabled(self) -> bool:
        return self._reject_popup_enabled

    ################################################################################
    # Overriden methods
    ################################################################################
    def accept(self):
        self._model.upsert(self._account)
        # model.commit()

        super().accept()

    def reject(self):
        # Only refresh account if existing account has changed.
        # If account is not attached to a session, that means it's a new account,
        # so we don't need to bother the user by confirming rejection.
        if self._account.hasSession() and self._account.hasChanged():
            print('reject(): changed attributes:', self._account.attributeNames(changed=True))

            if not self._reject_popup_enabled or self._askReject():
                self._account.refresh()
            else:
                return

        super().reject()

    ################################################################################
    # Internals
    ################################################################################
    def _askReject(self) -> bool:
        ret = QtWidgets.QMessageBox.question(
            self,
            'Account Changed',
            'Changed attributes of this account. Do you want to cancel editing?'
        )

        return ret == QtWidgets.QMessageBox.StandardButton.Yes

    def _updateAssetCombo(self, account_type: models.AccountType):
        if account_type != models.AccountType.Security:
            self._asset_lbl.setText('Currency')
            self._asset_combo.clear()
            self._asset_combo.addCurrencies(self._model.session())
        else:
            self._asset_lbl.setText('Security')
            self._asset_combo.clear()
            self._asset_combo.addSecurities(self._model.session())

        self._confirm_btn.setEnabled(self._asset_combo.count() > 0)

    @QtCore.pyqtSlot(str)
    def _onNameEdited(self, text: str):
        self._account.name = text
        self._confirm_btn.setEnabled(text != '')
    
    @QtCore.pyqtSlot(str)
    def _onDescriptionEdited(self, text: str):
        self._account.description = text

    @QtCore.pyqtSlot(models.AccountType)
    def _onCurrentAccountTypeChanged(self, account_type: models.AccountType):
        self._parent_tree.model().setFilterGroup(account_type.group())
        self._updateAssetCombo(account_type)

        self._account.type = account_type

    @QtCore.pyqtSlot(models.Asset)
    def _onCurrentAssetChanged(self, asset: models.Asset):
        self._account.asset = asset

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def _onParentTreeClicked(self, index: QtCore.QModelIndex):
        item = self._parent_tree.item(index)

        if item is None:
            return

        self._account.parent = item.account()

        if self._account.parent:
            self._type_combo.setCurrentAccountType(self._account.parent.type)