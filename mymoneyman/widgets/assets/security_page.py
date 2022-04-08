import typing
from PyQt5      import QtCore, QtWidgets
from mymoneyman import models, widgets

class SecurityPage(QtWidgets.QWidget):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._initWidgets()
        self._initLayouts()

    def _initWidgets(self):
        self._mic_combo = QtWidgets.QComboBox()
        self._mic_combo.currentIndexChanged.connect(self._onMICComboIndexChanged)

        self._add_security_btn = QtWidgets.QPushButton('Add')
        self._add_security_btn.clicked.connect(self._onAddSecurityButtonClicked)
        
        self._remove_security_btn = QtWidgets.QPushButton('Remove')
        self._remove_security_btn.clicked.connect(self._onRemoveSecurityButtonClicked)

        self._security_tree = widgets.assets.SecurityTreeWidget()
        self._security_tree.model().select()
        self._security_tree.expandAll()

        self._populateMICCombo()
    
    def _initLayouts(self):
        lcontrol_layout = QtWidgets.QHBoxLayout()
        lcontrol_layout.addWidget(self._mic_combo)
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

    def _populateMICCombo(self):
        prev_index = self._mic_combo.currentIndex()
        prev_text  = self._mic_combo.currentText()
        
        self._mic_combo.blockSignals(True)

        self._mic_combo.clear()
        self._mic_combo.addItem('All')
        self._mic_combo.addItems(self._security_tree.model().marketCodes())

        if prev_index < 1:
            self._mic_combo.setCurrentIndex(0)
        else:
            self._mic_combo.setCurrentText(prev_text)

        self._mic_combo.blockSignals(False)

    @QtCore.pyqtSlot()
    def _onAddSecurityButtonClicked(self):
        dialog = widgets.assets.SecurityEditDialog(self._security_tree.model())
        
        if dialog.exec():
            self._security_tree.expandAll()
            self._populateMICCombo()

    @QtCore.pyqtSlot()
    def _onRemoveSecurityButtonClicked(self):
        current_index = self._security_tree.currentIndex()
        current_item  = self._security_tree.model().itemFromIndex(current_index)

        if current_item is None:
            return

        if isinstance(current_item, models.SecurityTreeItem):
            ret = QtWidgets.QMessageBox.question(
                self,
                'Remove Security',
                f"Are you sure to remove security '{current_item.mic()}:{current_item.code()}'? This operation cannot be undone."
            )

            if ret == QtWidgets.QMessageBox.StandardButton.Yes:
                self._security_tree.model().delete(current_item.mic(), current_item.code())
                self._security_tree.expandAll()
                self._populateMICCombo()
        else:
            ret = QtWidgets.QMessageBox.question(
                self,
                'Remove Security',
                f"Are you sure to remove all securities in '{current_item.mic()}'? This operation cannot be undone."
            )

            if ret == QtWidgets.QMessageBox.StandardButton.Yes:
                self._security_tree.model().delete(current_item.mic())
                self._security_tree.expandAll()
                self._populateMICCombo()

    @QtCore.pyqtSlot(int)
    def _onMICComboIndexChanged(self, index: int):
        mic = self._mic_combo.currentText() if index > 0 else None

        self._security_tree.model().select(mic)
        self._security_tree.expandAll()