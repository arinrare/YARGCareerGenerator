"""About dialog."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QVBoxLayout,
    QPushButton,
)

from ... import __version__


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About YARG Career Builder")
        self.setFixedWidth(380)

        title = QLabel("YARG Career Builder")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)

        version = QLabel(f"Version {__version__}")
        version.setProperty("muted", True)
        version.setAlignment(Qt.AlignCenter)

        text = QLabel(
            "Build YARG career presets (portable Song-Tuple careers) "
            "from the song folders in your library."
        )
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignCenter)

        close = QPushButton("Close")
        close.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(version)
        layout.addSpacing(8)
        layout.addWidget(text)
        layout.addSpacing(12)
        layout.addWidget(close)
