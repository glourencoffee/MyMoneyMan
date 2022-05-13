import enum
import typing
from PyQt5 import QtGui, QtWidgets

class CaseLineEdit(QtWidgets.QLineEdit):
    """Implements a `QLineEdit` whose text is always cased.
    
    The class `CaseLineEdit` extends `QLineEdit` to implement a line edit that
    stores either an uppercase or lowercase text, depending on `Case`.

    It overrides the method `keyPressEvent()` so as to intercept user key presses
    and forward them to `QLineEdit` as uppercase or lowercase, according to the
    currently active `Case`, and overrides the method `setText()` to ensure that
    a programatically-defined text also respects that `Case`.
    """

    class Case(enum.IntEnum):
        Upper = 0
        Lower = 1

    def __init__(self, case: Case, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

        self._case = case

    def setText(self, text: str):
        pos  = super().cursorPosition()
        text = text.upper() if self._case == CaseLineEdit.Case.Upper else text.lower()

        super().setText(text)
        super().setCursorPosition(pos)

    def setCase(self, case: Case):
        if case == self._case:
            return

        self._case = case
        self.setText(self.text())

    def setUpperCase(self):
        self.setCase(CaseLineEdit.Case.Upper)

    def setLowerCase(self):
        self.setCase(CaseLineEdit.Case.Lower)

    def case(self) -> Case:
        return self._case

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Reimplements `QWidget.keyPressEvent()`."""

        text = event.text()
        text = text.upper() if self._case == CaseLineEdit.Case.Upper else text.lower()

        event = QtGui.QKeyEvent(
            event.type(),
            event.key(),
            event.modifiers(),
            event.nativeScanCode(),
            event.nativeVirtualKey(),
            event.nativeModifiers(),
            text,
            event.isAutoRepeat(),
            event.count()
        )

        return super().keyPressEvent(event)