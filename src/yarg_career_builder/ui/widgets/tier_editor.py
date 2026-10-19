"""Editable career structure (tier list + detail form)."""

import uuid

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .controls import NoScrollComboBox, NoScrollSpinBox

VENUE_HINTS = [
    "Venue/TunnelTrip",
    "Venue/Church",
    "Venue/MagiaAlliance",
    "Venue/OutdoorConcert",
    "Venue/Festival",
]


def _new_tier():
    return {
        "name": "New Tier",
        "song_count": 5,
        "unlock_criteria": 0,
        "is_bonus": False,
        "venue_hint": None,
        "custom_unlock_text": None,
        "id": str(uuid.uuid4()),
    }


def _copy_tier(tier):
    return {
        "name": tier.get("name") or "",
        "song_count": int(tier.get("song_count") or 0),
        "unlock_criteria": int(tier.get("unlock_criteria") or 0),
        "is_bonus": bool(tier.get("is_bonus", False)),
        "venue_hint": tier.get("venue_hint"),
        "custom_unlock_text": tier.get("custom_unlock_text"),
        "id": tier.get("id") or str(uuid.uuid4()),
    }


class TierEditor(QWidget):
    """Master-detail editor for the list of career tiers."""

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tiers = []
        self._index = -1

        # ---- left: tier list + controls --------------------------------
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._on_select)

        self.add_btn = QPushButton("Add")
        self.add_btn.setToolTip("Add a new tier.")
        self.add_btn.clicked.connect(self._add)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setToolTip("Remove the selected tier.")
        self.remove_btn.clicked.connect(self._remove)

        self.up_btn = QPushButton("Up")
        self.up_btn.setToolTip("Move the selected tier up.")
        self.up_btn.clicked.connect(lambda: self._move(-1))

        self.down_btn = QPushButton("Down")
        self.down_btn.setToolTip("Move the selected tier down.")
        self.down_btn.clicked.connect(lambda: self._move(1))

        btn_row = QHBoxLayout()
        for b in (self.add_btn, self.remove_btn, self.up_btn, self.down_btn):
            btn_row.addWidget(b)

        left = QVBoxLayout()
        left.addWidget(self.list_widget, 1)
        left.addLayout(btn_row)

        # ---- right: detail form ----------------------------------------
        self.name_edit = QLineEdit()
        self.name_edit.setToolTip("Tier name shown in the career.")
        self.name_edit.textChanged.connect(self._on_edit)

        self.songs_spin = NoScrollSpinBox()
        self.songs_spin.setRange(1, 1000)
        self.songs_spin.setToolTip("Relative number of songs in this tier (used to split the selected songs).")
        self.songs_spin.valueChanged.connect(self._on_edit)

        self.unlock_spin = NoScrollSpinBox()
        self.unlock_spin.setRange(0, 100000)
        self.unlock_spin.setToolTip("Stars required to unlock this tier.")
        self.unlock_spin.valueChanged.connect(self._on_edit)

        self.bonus_check = QCheckBox("Bonus tier")
        self.bonus_check.setToolTip("Bonus tiers are optional side-setlists.")
        self.bonus_check.toggled.connect(self._on_edit)

        self.venue_combo = NoScrollComboBox()
        self.venue_combo.setEditable(True)
        self.venue_combo.addItem("")
        self.venue_combo.addItems(VENUE_HINTS)
        self.venue_combo.setToolTip("Optional venue for this tier. Pick one or type a custom Venue/<name>.")
        self.venue_combo.currentTextChanged.connect(self._on_edit)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Optional flavour text shown when the tier unlocks.")
        self.text_edit.setToolTip("Custom unlock text shown to the player.")
        self.text_edit.textChanged.connect(self._on_edit)

        form_group = QGroupBox("Tier details")
        form = QFormLayout(form_group)
        form.setLabelAlignment(form.labelAlignment())
        form.addRow("Name", self.name_edit)
        form.addRow("Song count", self.songs_spin)
        form.addRow("Unlock criteria", self.unlock_spin)
        form.addRow("", self.bonus_check)
        form.addRow("Venue hint", self.venue_combo)
        form.addRow("Unlock text", self.text_edit)

        right = QVBoxLayout()
        right.addWidget(form_group)
        right.addStretch(1)

        # ---- layout ----------------------------------------------------
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(left, 1)
        layout.addLayout(right, 2)

        self._refresh()

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def set_tiers(self, tiers):
        self._commit()
        self._tiers = [_copy_tier(t) for t in tiers]
        self._index = 0 if self._tiers else -1
        self._refresh()

    def tiers(self):
        self._commit()
        return [_copy_tier(t) for t in self._tiers]

    # ------------------------------------------------------------------ #
    #  Internals
    # ------------------------------------------------------------------ #

    def _refresh(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for i, t in enumerate(self._tiers):
            label = f"{i + 1}. {t['name']}  ({t['song_count']} songs)"
            item = QListWidgetItem(label)
            self.list_widget.addItem(item)
        if self._tiers:
            self.list_widget.setCurrentRow(self._index if 0 <= self._index < len(self._tiers) else 0)
        self.list_widget.blockSignals(False)

        has = bool(self._tiers)
        self.remove_btn.setEnabled(has)
        self.up_btn.setEnabled(has)
        self.down_btn.setEnabled(has)
        self.name_edit.setEnabled(has)
        self.songs_spin.setEnabled(has)
        self.unlock_spin.setEnabled(has)
        self.bonus_check.setEnabled(has)
        self.venue_combo.setEnabled(has)
        self.text_edit.setEnabled(has)

        self._load_detail()

    def _load_detail(self):
        self._block_signals(True)
        if 0 <= self._index < len(self._tiers):
            t = self._tiers[self._index]
            self.name_edit.setText(t["name"])
            self.songs_spin.setValue(t["song_count"])
            self.unlock_spin.setValue(t["unlock_criteria"])
            self.bonus_check.setChecked(t["is_bonus"])
            self.venue_combo.setCurrentText(t["venue_hint"] or "")
            self.text_edit.setPlainText(t["custom_unlock_text"] or "")
        else:
            self.name_edit.clear()
            self.songs_spin.setValue(5)
            self.unlock_spin.setValue(0)
            self.bonus_check.setChecked(False)
            self.venue_combo.setCurrentText("")
            self.text_edit.clear()
        self._block_signals(False)

    def _commit(self):
        if 0 <= self._index < len(self._tiers):
            t = self._tiers[self._index]
            t["name"] = self.name_edit.text().strip()
            t["song_count"] = int(self.songs_spin.value())
            t["unlock_criteria"] = int(self.unlock_spin.value())
            t["is_bonus"] = self.bonus_check.isChecked()
            t["venue_hint"] = self.venue_combo.currentText().strip() or None
            t["custom_unlock_text"] = self.text_edit.toPlainText().strip() or None

    def _block_signals(self, blocked):
        for w in (self.name_edit, self.songs_spin, self.unlock_spin, self.bonus_check, self.venue_combo, self.text_edit):
            w.blockSignals(blocked)

    def _on_select(self, row):
        if row < 0:
            return
        self._commit()
        self._index = row
        self._load_detail()

    def _on_edit(self, *args):
        if 0 <= self._index < len(self._tiers):
            self._commit()
            self.list_widget.item(self._index).setText(
                f"{self._index + 1}. {self._tiers[self._index]['name']}  ({self._tiers[self._index]['song_count']} songs)"
            )
        self.changed.emit()

    def _add(self):
        self._commit()
        self._tiers.append(_new_tier())
        self._index = len(self._tiers) - 1
        self._refresh()
        self.changed.emit()

    def _remove(self):
        if not self._tiers:
            return
        self._commit()
        del self._tiers[self._index]
        self._index = max(0, min(self._index, len(self._tiers) - 1)) if self._tiers else -1
        self._refresh()
        self.changed.emit()

    def _move(self, delta):
        self._commit()
        new_index = self._index + delta
        if not (0 <= new_index < len(self._tiers)):
            return
        self._tiers[self._index], self._tiers[new_index] = self._tiers[new_index], self._tiers[self._index]
        self._index = new_index
        self._refresh()
        self.changed.emit()
