"""Dark theme for the application (QSS + QPalette)."""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# Accent colour used for selection / highlights.
ACCENT = "#7c5cff"

_QSS = """
* {
    font-family: "Segoe UI", "Helvetica Neue", sans-serif;
    font-size: 13px;
}

QMainWindow, QDialog {
    background-color: #1e1f24;
}

QWidget {
    background-color: #1e1f24;
    color: #e6e6ea;
}

QMenuBar {
    background-color: #18191d;
    color: #e6e6ea;
    border-bottom: 1px solid #2a2b30;
}
QMenuBar::item {
    background: transparent;
    padding: 5px 10px;
}
QMenuBar::item:selected {
    background-color: #2a2b30;
    border-radius: 4px;
}
QMenu {
    background-color: #232429;
    color: #e6e6ea;
    border: 1px solid #2f3036;
}
QMenu::item {
    padding: 5px 24px 5px 20px;
}
QMenu::item:selected {
    background-color: #33343b;
}
QMenu::separator {
    height: 1px;
    background: #2f3036;
    margin: 4px 8px;
}

QGroupBox {
    border: 1px solid #2f3036;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #15161a;
    border: 1px solid #33343b;
    border-radius: 4px;
    padding: 5px 8px;
    color: #e6e6ea;
    selection-background-color: @ACCENT@;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid @ACCENT@;
}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {
    color: #6a6b70;
    background-color: #1a1b1f;
}

QComboBox::drop-down {
    border: none;
    width: 22px;
}
QComboBox QAbstractItemView {
    background-color: #232429;
    color: #e6e6ea;
    border: 1px solid #2f3036;
    selection-background-color: @ACCENT@;
    selection-color: #ffffff;
    outline: 0;
}

QPushButton {
    background-color: #2b2c33;
    border: 1px solid #3a3b42;
    border-radius: 5px;
    padding: 6px 14px;
    color: #e6e6ea;
}
QPushButton:hover {
    background-color: #33343b;
}
QPushButton:pressed {
    background-color: #26272d;
}
QPushButton:disabled {
    color: #6a6b70;
    background-color: #1f2024;
    border-color: #2b2c31;
}
QPushButton[accent="true"] {
    background-color: @ACCENT@;
    border: 1px solid @ACCENT@;
    color: #ffffff;
    font-weight: bold;
}
QPushButton[accent="true"]:hover {
    background-color: #8a6fff;
}
QPushButton[accent="true"]:pressed {
    background-color: #6b4fe6;
}
QPushButton[accent="true"]:disabled {
    background-color: #3a3a4a;
    border-color: #3a3a4a;
    color: #9a9aa5;
}

QTabWidget::pane {
    border: 1px solid #2f3036;
    border-radius: 6px;
    top: -1px;
}
QTabBar::tab {
    background: transparent;
    color: #a0a1a8;
    padding: 7px 18px;
    margin-right: 2px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
}
QTabBar::tab:selected {
    background-color: #2b2c33;
    color: #ffffff;
}
QTabBar::tab:hover:!selected {
    background-color: #232429;
}

QTableWidget, QTableView {
    background-color: #15161a;
    alternate-background-color: #1b1c21;
    color: #e6e6ea;
    gridline-color: #26272d;
    border: 1px solid #2f3036;
    border-radius: 4px;
    selection-background-color: @ACCENT@;
    selection-color: #ffffff;
}
QHeaderView::section {
    background-color: #232429;
    color: #c0c1c8;
    padding: 6px 8px;
    border: none;
    border-right: 1px solid #2f3036;
    border-bottom: 1px solid #2f3036;
    font-weight: bold;
}
QTableCornerButton::section {
    background-color: #232429;
    border: none;
}

QCheckBox {
    spacing: 7px;
    color: #e6e6ea;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #3a3b42;
    background-color: #15161a;
}
QCheckBox::indicator:checked {
    background-color: @ACCENT@;
    border: 1px solid @ACCENT@;
}

QPlainTextEdit, QTextEdit {
    background-color: #15161a;
    color: #c9cad2;
    border: 1px solid #2f3036;
    border-radius: 4px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
}

QProgressBar {
    background-color: #15161a;
    border: 1px solid #2f3036;
    border-radius: 4px;
    text-align: center;
    color: #e6e6ea;
    height: 18px;
}
QProgressBar::chunk {
    background-color: @ACCENT@;
    border-radius: 3px;
}

QScrollBar:vertical {
    background: #1e1f24;
    width: 12px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #3a3b42;
    border-radius: 6px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #4a4b52;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #1e1f24;
    height: 12px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #3a3b42;
    border-radius: 6px;
    min-width: 24px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

QLabel {
    color: #e6e6ea;
}
QLabel[muted="true"] {
    color: #8a8b92;
}

QStatusBar {
    background-color: #18191d;
    color: #a0a1a8;
    border-top: 1px solid #2a2b30;
}

QToolTip {
    background-color: #232429;
    color: #e6e6ea;
    border: 1px solid #3a3b42;
}

QFrame[tag="true"] {
    background-color: #33343b;
    border: 1px solid #3a3b42;
    border-radius: 13px;
}
QFrame[tag="true"] QLabel {
    background: transparent;
    color: #e6e6ea;
}
QFrame[tag="true"] QSpinBox {
    background-color: #15161a;
}
QPushButton[chipClose="true"] {
    background: transparent;
    border: none;
    color: #a0a1a8;
    font-weight: bold;
    padding: 0;
}
QPushButton[chipClose="true"]:hover {
    color: #ffffff;
    background-color: #4a4b52;
    border-radius: 10px;
}
"""
_QSS = _QSS.replace("@ACCENT@", ACCENT)


def apply_theme(app: QApplication, dark: bool = True):
    """Apply the Fusion style, palette and QSS to the application."""
    app.setStyle("Fusion")

    if dark:
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#1e1f24"))
        palette.setColor(QPalette.WindowText, QColor("#e6e6ea"))
        palette.setColor(QPalette.Base, QColor("#15161a"))
        palette.setColor(QPalette.AlternateBase, QColor("#1b1c21"))
        palette.setColor(QPalette.ToolTipBase, QColor("#232429"))
        palette.setColor(QPalette.ToolTipText, QColor("#e6e6ea"))
        palette.setColor(QPalette.Text, QColor("#e6e6ea"))
        palette.setColor(QPalette.Button, QColor("#2b2c33"))
        palette.setColor(QPalette.ButtonText, QColor("#e6e6ea"))
        palette.setColor(QPalette.BrightText, QColor("#ffffff"))
        palette.setColor(QPalette.Highlight, QColor(ACCENT))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        palette.setColor(QPalette.Link, QColor(ACCENT))
        palette.setColor(QPalette.PlaceholderText, QColor("#6a6b70"))
        app.setPalette(palette)
        app.setStyleSheet(_QSS)
    else:
        app.setStyleSheet("")
        app.setPalette(app.style().standardPalette())
