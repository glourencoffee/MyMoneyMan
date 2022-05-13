import sqlalchemy.orm as sa_orm
import typing
from PyQt5      import QtCore, QtWidgets
from mymoneyman import models, widgets

class SecurityPage(QtWidgets.QWidget):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

        self._security_table_model = models.SecurityTableModel()

        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        self._market_combo = QtWidgets.QComboBox()
        self._market_combo.currentIndexChanged.connect(self._onMarketComboIndexChanged)

        self._add_security_btn = QtWidgets.QPushButton('Add')
        self._add_security_btn.clicked.connect(self._onAddSecurityButtonClicked)
        
        self._remove_security_btn = QtWidgets.QPushButton('Remove')
        self._remove_security_btn.clicked.connect(self._onRemoveSecurityButtonClicked)

        self._security_tree = widgets.SecurityTreeWidget()
        self._security_tree.setSourceModel(self._security_table_model)
        # self._security_tree.model().select()
        self._security_tree.expandAll()

        self._populateMICCombo()
    
    def _initLayouts(self):
        lcontrol_layout = QtWidgets.QHBoxLayout()
        lcontrol_layout.addWidget(self._market_combo)
        lcontrol_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

        rcontrol_layout = QtWidgets.QHBoxLayout()
        rcontrol_layout.addWidget(self._add_security_btn)
        rcontrol_layout.addWidget(self._remove_security_btn)
        rcontrol_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        control_layout = QtWidgets.QHBoxLayout()
        control_layout.addLayout(lcontrol_layout)
        control_layout.addLayout(rcontrol_layout)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self._security_tree)
    
        self.setLayout(main_layout)

    def setSession(self, session: sa_orm.Session):
        self._security_table_model.select(session)

    def _populateMICCombo(self):
        prev_index = self._market_combo.currentIndex()
        prev_text  = self._market_combo.currentText()
        
        self._market_combo.blockSignals(True)

        self._market_combo.clear()
        self._market_combo.addItem('All')
        # self._market_combo.addItems(self._security_tree.model().markets())

        if prev_index < 1:
            self._market_combo.setCurrentIndex(0)
        else:
            self._market_combo.setCurrentText(prev_text)

        self._market_combo.blockSignals(False)

    @QtCore.pyqtSlot()
    def _onAddSecurityButtonClicked(self):
        dialog = widgets.SecurityEditDialog(self._security_table_model)
        dialog.exec()

    @QtCore.pyqtSlot()
    def _onRemoveSecurityButtonClicked(self):
        index = self._security_tree.currentIndex()
        model = self._security_tree.model()

        item: typing.Optional[models.SecurityTreeProxyItem] = model.itemFromIndex(index)

        if item is None:
            return

        if item.isMarket():
            return
            # ret = QtWidgets.QMessageBox.question(
            #     self,
            #     'Remove Security',
            #     f"Are you sure to remove all securities in '{item}'?"
            # )

            # if ret == QtWidgets.QMessageBox.StandardButton.Yes:
            #     for security in model.securities(item):
            #         model.delete(security)

            #     self._security_tree.expandAll()
            #     self._populateMICCombo()
        else:
            print('item ==', item)
            ret = QtWidgets.QMessageBox.question(
                self,
                'Remove Security',
                f"Are you sure to remove security '{item.market()}:{item.code()}'?"
            )

            if ret == QtWidgets.QMessageBox.StandardButton.Yes:
                self._security_table_model.delete(item.security())
                # self._security_tree.expandAll()
                # self._populateMICCombo()

    @QtCore.pyqtSlot(int)
    def _onMarketComboIndexChanged(self, index: int):
        market = self._market_combo.currentText() if index > 0 else None

        self._security_tree.model().select(market)
        self._security_tree.expandAll()