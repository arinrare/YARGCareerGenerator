"""Qt application entry point."""

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .paths import BUNDLED
from .ui.theme import apply_theme
from .ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("YARG Career Builder")
    app.setApplicationDisplayName("YARG Career Builder")
    app.setOrganizationName("YARG Careers")

    icon_path = BUNDLED / "assets" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    apply_theme(app, dark=True)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
