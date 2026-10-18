"""Reusable folder/file picker row."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QWidget,
)


class PathPicker(QWidget):
    """A labelled path field with a Browse button.

    mode: "folder" (pick a directory) or "file" (pick a single file).
    """

    pathChanged = Signal(str)

    def __init__(self, label, mode="folder", parent=None, dialog_title=None, hint=None):
        super().__init__(parent)
        self._mode = mode
        self._dialog_title = dialog_title or ("Choose folder" if mode == "folder" else "Choose file")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.edit = QLineEdit()
        self.edit.setPlaceholderText(label)
        self.edit.textChanged.connect(self.pathChanged.emit)
        if hint:
            self.edit.setToolTip(hint)

        self.button = QPushButton("Browse…")
        self.button.clicked.connect(self._browse)

        layout.addWidget(self.edit, 1)
        layout.addWidget(self.button)

    def _browse(self):
        if self._mode == "folder":
            path = QFileDialog.getExistingDirectory(self, self._dialog_title, self.edit.text())
        else:
            path, _ = QFileDialog.getOpenFileName(self, self._dialog_title, self.edit.text())
        if path:
            self.edit.setText(path)

    def setText(self, text):
        self.edit.setText(text)

    def text(self):
        return self.edit.text().strip()
