"""Input widgets that don't swallow the mouse wheel while closed/unfocused."""

from PySide6.QtWidgets import QComboBox, QSpinBox


class NoScrollComboBox(QComboBox):
    """A combo box that only responds to the wheel while its popup is open."""

    def wheelEvent(self, event):
        if self.view().isVisible():
            super().wheelEvent(event)
        else:
            event.ignore()


class NoScrollSpinBox(QSpinBox):
    """A spin box that only responds to the wheel while it has focus."""

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()
