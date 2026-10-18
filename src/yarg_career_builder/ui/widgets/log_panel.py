"""Read-only log/output panel."""

from PySide6.QtWidgets import QPlainTextEdit


class LogPanel(QPlainTextEdit):
    """Read-only, monospace output panel with append helpers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(2000)

    def log(self, text=""):
        self.appendPlainText(text)

    def error(self, text):
        self.appendPlainText(text)
