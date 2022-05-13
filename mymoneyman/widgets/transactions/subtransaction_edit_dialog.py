import typing
from PyQt5      import QtCore, QtGui, QtWidgets
from mymoneyman import models, widgets

class SubtransactionEditDialog(QtWidgets.QDialog):
    def __init__(self,
                 model: models.AccountTableModel,
                 transaction: models.Transaction,
                 parent: typing.Optional[QtWidgets.QWidget] = None
    ):
        super().__init__(parent=parent)

        self._initWidgets(model)
        self._initLayouts()

        self._subtransaction_table.model().setTransaction(transaction)
    
    def _initWidgets(self, model: models.AccountTableModel):
        self.setWindowTitle('Split Transaction')
        self.setMinimumSize(QtCore.QSize(600, 200))

        self._subtransaction_table = widgets.SubtransactionTableWidget(model)
        self._subtransaction_table.model().modelReset.connect(self.validate)
        self._subtransaction_table.model().dataChanged.connect(self._onModelDataChanged)

        self._append_btn = QtWidgets.QPushButton('Append')
        self._append_btn.clicked.connect(self._onAppendButtonClicked)

        self._remove_btn = QtWidgets.QPushButton('Remove')
        self._remove_btn.clicked.connect(self._onRemoveButtonClicked)

        self._confirm_btn = QtWidgets.QPushButton('Confirm')
        self._confirm_btn.clicked.connect(self.accept)

        self._cancel_btn = QtWidgets.QPushButton('Cancel')
        self._cancel_btn.clicked.connect(self.reject)

        self.validate()

    def _initLayouts(self):
        top_buttons_layout = QtWidgets.QVBoxLayout()
        top_buttons_layout.addWidget(self._append_btn)
        top_buttons_layout.addWidget(self._remove_btn)
        top_buttons_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        
        bottom_buttons_layout = QtWidgets.QVBoxLayout()
        bottom_buttons_layout.addWidget(self._confirm_btn)
        bottom_buttons_layout.addWidget(self._cancel_btn)
        bottom_buttons_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignBottom)

        buttons_layout = QtWidgets.QVBoxLayout()
        buttons_layout.addLayout(top_buttons_layout)
        buttons_layout.addLayout(bottom_buttons_layout)

        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addWidget(self._subtransaction_table)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

    def transaction(self) -> models.Transaction:
        return self._subtransaction_table.model().transaction()

    def validate(self):
        model = self._subtransaction_table.model()

        if model.rowCount() > 0:
            all_valid = True

            for sub in model.subtransactions():
                if sub.origin is None or sub.target is None:
                    all_valid = False
                    break
        else:
            all_valid = False

        self._confirm_btn.setEnabled(all_valid)

    @QtCore.pyqtSlot(QtCore.QModelIndex, QtCore.QModelIndex, 'QVector<int>')
    def _onModelDataChanged(self, top_left: QtCore.QModelIndex, bottom_right: QtCore.QModelIndex, roles: typing.Iterable[str]):
        self.validate()

    @QtCore.pyqtSlot()
    def _onAppendButtonClicked(self):
        self._subtransaction_table.model().appendSubtransaction()
        self._remove_btn.setEnabled(True)
        self.validate()

    @QtCore.pyqtSlot()
    def _onRemoveButtonClicked(self):
        model         = self._subtransaction_table.model()
        current_index = self._subtransaction_table.currentIndex()

        if not current_index.isValid():
            return

        model.removeSubtransaction(current_index.row())

        if model.rowCount() == 0:
            self._remove_btn.setEnabled(False)