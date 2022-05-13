import os
import sqlalchemy       as sa
import sqlalchemy.orm   as sa_orm
import sqlalchemy.exc   as sa_exc
import sqlalchemy.event as sa_event
from PyQt5      import QtCore, QtWidgets
from mymoneyman import models, widgets

class MainWindow(QtWidgets.QMainWindow):
    """Implements the main window shown by the application."""

    def __init__(self):
        super().__init__()

        self._engine  = None
        self._session = None

        self._initWidgets()
        self._initMenuBar()
    
    def _initWidgets(self):
        self._account_page = widgets.AccountPage()
        self._account_page.accountCreated.connect(self._onAccountCreated)
        self._account_page.accountDeleted.connect(self._onAccountDeleted)
        self._account_page.accountEdited.connect(self._onAccountEdited)
        self._account_page.accountDoubleClicked.connect(self._onAccountDoubleClicked)

        self._transaction_page = widgets.TransactionPage(self._account_page._account_table_model)
        self._transaction_page.transactionChanged.connect(lambda t: self._account_page.refresh)

        self._currency_page = widgets.CurrencyPage()
        self._security_page = widgets.SecurityPage()

        self._quote_model = models.SubtransactionQuoteModel()
        self._quote_view = QtWidgets.QTableView()
        self._quote_view.setModel(self._quote_model)

        #TODO: tr()
        self._pages = QtWidgets.QTabWidget()
        self._pages.addTab(self._account_page,     'Accounts')
        self._pages.addTab(self._transaction_page, 'Transactions')
        self._pages.addTab(self._currency_page,    'Currencies')
        self._pages.addTab(self._security_page,    'Securities')
        self._pages.addTab(self._quote_view,       'Quotes')
        self._pages.setEnabled(False)

        self.setCentralWidget(self._pages)

    def _initMenuBar(self):
        file_menu = self.menuBar().addMenu('File')
        
        self._open_action = file_menu.addAction('Open account book...', self._onOpenActionTriggered)

        self._save_action = file_menu.addAction('Save', self.commit)
        self._save_action.setEnabled(False)

        self._cancel_action = file_menu.addAction('Cancel', self.rollback)
        self._cancel_action.setEnabled(False)

        help_menu = self.menuBar().addMenu('Help')
        help_menu.addAction('About', lambda: QtWidgets.QMessageBox.aboutQt(self))

    def askReset(self) -> bool:
        if self._session is None:
            return True
        
        has_changed = any(self._session.is_modified(mapped_obj) for mapped_obj in self._session.dirty)

        if not has_changed:
            return True
        
        ret = QtWidgets.QMessageBox.question(
            self,
            'Database Changed',
            'The database has pending changes. Do you want to save them?',
            (
                QtWidgets.QMessageBox.StandardButton.Yes |
                QtWidgets.QMessageBox.StandardButton.No  |
                QtWidgets.QMessageBox.StandardButton.Cancel
            )
        )

        if ret == QtWidgets.QMessageBox.StandardButton.Cancel:
            return False
        
        if ret == QtWidgets.QMessageBox.StandardButton.Yes:
            self._session.commit()

        return True

    def setFileEngine(self, filepath: str, echo: bool = False):
        if not self.askReset():
            return

        self._engine  = sa.create_engine(f'sqlite:///{filepath}', echo=echo, future=True)
        self._session = sa_orm.Session(self._engine)
        
        sa_event.listen(self._session, 'after_flush', self._onAfterFlushSession)
        
        models.AlchemicalBase.metadata.create_all(self._engine)

        self._account_page.setSession(self._session)
        self._transaction_page.setSession(self._session)
        self._currency_page.setSession(self._session)
        self._security_page.setSession(self._session)
        self._quote_model.select(self._session)

        self.setWindowTitle(os.path.split(filepath)[1] + ' - MyMoneyMan')

    def commit(self):
        if self._session is None:
            return
        
        self._session.commit()

    def rollback(self):
        if self._session is None:
            return
        
        self._session.rollback()

    def _onAfterFlushSession(self, session, flush_context):
        self.setWindowTitle('*' + self.windowTitle())

    @QtCore.pyqtSlot()
    def _onOpenActionTriggered(self):
        dialog = QtWidgets.QFileDialog(self)
        
        if not dialog.exec():
            return

        files = dialog.selectedFiles()

        if len(files) == 0:
            return

        file = files[0]

        try:
            self.setFileEngine(file)
        except sa_exc.DatabaseError:
            QtWidgets.QMessageBox.critical(self, 'Database Error', 'File is not a database.')
            return
        
        self._save_action.setEnabled(True)
        self._cancel_action.setEnabled(True)
        self._pages.setEnabled(True)

    @QtCore.pyqtSlot(models.Account)
    def _onAccountCreated(self, account: models.Account):
        pass
    
    @QtCore.pyqtSlot(models.Account)
    def _onAccountDeleted(self, account: models.Account):
        pass
    
    @QtCore.pyqtSlot(models.Account)
    def _onAccountEdited(self, account: models.Account):
        pass

    @QtCore.pyqtSlot(models.Account)
    def _onAccountDoubleClicked(self, account: models.Account):
        self._transaction_page.setCurrentAccount(account)
        self._pages.setCurrentWidget(self._transaction_page)