"""Editable career structure (tier list + detail form)."""

import os
import shutil
import uuid

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...paths import MEDIA_DIR
from .controls import NoScrollComboBox, NoScrollSpinBox

VENUE_HINTS = [
    "Venue/TunnelTrip",
    "Venue/Church",
    "Venue/MagiaAlliance",
    "Venue/OutdoorConcert",
    "Venue/Festival",
]

UNLOCK_TYPES = ["StarCount", "CompletionCount"]
VENUE_SIZES = ["NotSpecified", "Starter", "Small", "Medium", "Large", "Epic"]
COMPLETION_MODES = ["SingleSong", "FullTierPlaylist", "FullCareerPlaylist"]
COMPLETION_BONUSES = ["None", "Image", "Sound", "Video"]

MEDIA_FILTERS = {
    "Image": "Images (*.png *.jpg *.jpeg)",
    "Sound": "Audio (*.ogg *.mp3 *.wav *.flac)",
    "Video": "Videos (*.webm)",
}


def _new_tier():
    return {
        "name": "New Tier",
        "description": None,
        "song_count": 5,
        "unlock_type": "StarCount",
        "unlock_criteria": 0,
        "is_bonus": False,
        "venue_size": "NotSpecified",
        "venue_hint": None,
        "completion_mode": "SingleSong",
        "custom_unlock_text": None,
        "completion_bonus": "None",
        "completion_bonus_text": None,
        "media_path": None,
        "id": str(uuid.uuid4()),
    }


def _copy_tier(tier):
    return {
        "name": tier.get("name") or "",
        "description": tier.get("description"),
        "song_count": int(tier.get("song_count") or 0),
        "unlock_type": tier.get("unlock_type") or "StarCount",
        "unlock_criteria": int(tier.get("unlock_criteria") or 0),
        "is_bonus": bool(tier.get("is_bonus", False)),
        "venue_size": tier.get("venue_size") or "NotSpecified",
        "venue_hint": tier.get("venue_hint"),
        "completion_mode": tier.get("completion_mode") or "SingleSong",
        "custom_unlock_text": tier.get("custom_unlock_text"),
        "completion_bonus": tier.get("completion_bonus") or "None",
        "completion_bonus_text": tier.get("completion_bonus_text"),
        "media_path": tier.get("media_path"),
        "id": tier.get("id") or str(uuid.uuid4()),
    }


def _set_text(combo, value):
    idx = combo.findText(value or "")
    combo.setCurrentIndex(idx if idx >= 0 else 0)


def _is_managed_media(path):
    if not path:
        return False
    base = os.path.abspath(str(MEDIA_DIR))
    return os.path.abspath(path).startswith(base + os.sep)


class TierEditor(QWidget):
    """Master-detail editor for the list of career tiers."""

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tiers = []
        self._index = -1
        self._media_dir = MEDIA_DIR

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
        self.name_edit.textChanged.connect(self._on_edit)

        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Optional tier description.")
        self.description_edit.textChanged.connect(self._on_edit)

        self.songs_spin = NoScrollSpinBox()
        self.songs_spin.setRange(1, 1000)
        self.songs_spin.valueChanged.connect(self._on_edit)

        self.unlock_type_combo = NoScrollComboBox()
        self.unlock_type_combo.addItems(UNLOCK_TYPES)
        self.unlock_type_combo.currentTextChanged.connect(self._on_edit)

        self.unlock_spin = NoScrollSpinBox()
        self.unlock_spin.setRange(0, 100000)
        self.unlock_spin.valueChanged.connect(self._on_edit)

        self.bonus_check = QCheckBox("Bonus tier")
        self.bonus_check.toggled.connect(self._on_edit)

        self.venue_size_combo = NoScrollComboBox()
        self.venue_size_combo.addItems(VENUE_SIZES)
        self.venue_size_combo.currentTextChanged.connect(self._on_edit)

        self.venue_combo = NoScrollComboBox()
        self.venue_combo.setEditable(True)
        self.venue_combo.addItem("")
        self.venue_combo.addItems(VENUE_HINTS)
        self.venue_combo.currentTextChanged.connect(self._on_edit)

        self.completion_mode_combo = NoScrollComboBox()
        self.completion_mode_combo.addItems(COMPLETION_MODES)
        self.completion_mode_combo.currentTextChanged.connect(self._on_edit)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Optional flavour text shown when the tier unlocks.")
        self.text_edit.textChanged.connect(self._on_edit)

        self.completion_bonus_combo = NoScrollComboBox()
        self.completion_bonus_combo.addItems(COMPLETION_BONUSES)
        self.completion_bonus_combo.currentTextChanged.connect(self._on_edit)

        self.bonus_text_edit = QLineEdit()
        self.bonus_text_edit.setPlaceholderText("Optional text shown when the completion bonus triggers.")
        self.bonus_text_edit.textChanged.connect(self._on_edit)

        self.media_label = QLabel("(none)")
        self.media_label.setProperty("muted", True)
        self.media_choose_btn = QPushButton("Choose…")
        self.media_choose_btn.clicked.connect(self._on_choose_media)
        self.media_clear_btn = QPushButton("Clear")
        self.media_clear_btn.clicked.connect(self._on_clear_media)
        media_row = QHBoxLayout()
        media_row.addWidget(self.media_label, 1)
        media_row.addWidget(self.media_choose_btn)
        media_row.addWidget(self.media_clear_btn)

        form_group = QGroupBox("Tier details")
        form = QFormLayout(form_group)
        form.setLabelAlignment(form.labelAlignment())
        self._add_row(form, "Name", self.name_edit,
                      "The tier's display name shown in the career menu.")
        self._add_row(form, "Description", self.description_edit,
                      "Optional flavour text describing this tier. Stored in the preset.")
        self._add_row(form, "Song count", self.songs_spin,
                      "Relative number of songs in this tier (used to split the selected songs).")
        self._add_row(form, "Unlock type", self.unlock_type_combo,
                      "Star Count — unlock when the running star total reaches the criteria.\n"
                      "Completion Count — unlock when the number of completed songs reaches the criteria.")
        self._add_row(form, "Unlock criteria", self.unlock_spin,
                      "Stars (Star Count) or completed songs (Completion Count) required to unlock this tier. "
                      "Bonus tiers don't count toward this total.")
        self._add_row(form, "Bonus tier", self.bonus_check,
                      "Optional side-setlist. Bonus tiers don't contribute to unlocking later tiers.")
        self._add_row(form, "Venue size", self.venue_size_combo,
                      "Approximate stage size used for venue selection:\n"
                      "NotSpecified / Starter / Small / Medium / Large / Epic.")
        self._add_row(form, "Venue hint", self.venue_combo,
                      "Optional venue path (e.g. Venue/Church). Pick one or type a custom Venue/<name>.")
        self._add_row(form, "Completion mode", self.completion_mode_combo,
                      "SingleSong — finish each song to complete the tier.\n"
                      "FullTierPlaylist / FullCareerPlaylist — play through as a playlist.\n"
                      "Playlist modes are stored but not yet honored by YARG gameplay.")
        self._add_row(form, "Unlock text", self.text_edit,
                      "Custom flavour text shown to the player when the tier unlocks.")
        self._add_row(form, "Completion bonus", self.completion_bonus_combo,
                      "What to show when the tier is completed: None / Image / Sound / Video.")
        self._add_row(form, "Bonus text", self.bonus_text_edit,
                      "Text shown when the completion bonus triggers.")
        self._add_row(form, "Media file", media_row,
                      "Pick the image (png/jpg/jpeg), video (webm), or audio (ogg/mp3/wav/flac) "
                      "shown/played when the tier completes. Copied into the app's media folder and "
                      "embedded in the exported .preset.")
        self.media_choose_btn.setToolTip(
            "Pick the media file shown/played when the tier completes. "
            "Copied into the app's media folder and embedded in the exported .preset.")
        self.media_clear_btn.setToolTip("Remove the tier's completion-bonus media file.")

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

    def set_media_dir(self, path):
        """Set the folder where picked media files are copied (per career)."""
        self._media_dir = path

    # ------------------------------------------------------------------ #
    #  Internals
    # ------------------------------------------------------------------ #

    @staticmethod
    def _add_row(form, label_text, widget, tooltip):
        if isinstance(widget, QHBoxLayout):
            widget = TierEditor._wrap_layout(widget)
        form.addRow(label_text, widget)
        widget.setToolTip(tooltip)
        label = form.labelForField(widget)
        if label is not None:
            label.setToolTip(tooltip)

    @staticmethod
    def _wrap_layout(layout):
        w = QWidget()
        w.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        return w

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
        for w in self._detail_widgets():
            w.setEnabled(has)

        self._load_detail()

    def _detail_widgets(self):
        return (
            self.name_edit,
            self.description_edit,
            self.songs_spin,
            self.unlock_type_combo,
            self.unlock_spin,
            self.bonus_check,
            self.venue_size_combo,
            self.venue_combo,
            self.completion_mode_combo,
            self.text_edit,
            self.completion_bonus_combo,
            self.bonus_text_edit,
            self.media_choose_btn,
            self.media_clear_btn,
        )

    def _load_detail(self):
        self._block_signals(True)
        if 0 <= self._index < len(self._tiers):
            t = self._tiers[self._index]
            self.name_edit.setText(t["name"])
            self.description_edit.setText(t["description"] or "")
            self.songs_spin.setValue(t["song_count"])
            _set_text(self.unlock_type_combo, t["unlock_type"])
            self.unlock_spin.setValue(t["unlock_criteria"])
            self.bonus_check.setChecked(t["is_bonus"])
            _set_text(self.venue_size_combo, t["venue_size"])
            self.venue_combo.setCurrentText(t["venue_hint"] or "")
            _set_text(self.completion_mode_combo, t["completion_mode"])
            self.text_edit.setPlainText(t["custom_unlock_text"] or "")
            _set_text(self.completion_bonus_combo, t["completion_bonus"])
            self.bonus_text_edit.setText(t["completion_bonus_text"] or "")
            self.media_label.setText(os.path.basename(t["media_path"]) if t["media_path"] else "(none)")
            self.media_clear_btn.setEnabled(bool(t["media_path"]))
        else:
            self.name_edit.clear()
            self.description_edit.clear()
            self.songs_spin.setValue(5)
            self.unlock_type_combo.setCurrentIndex(0)
            self.unlock_spin.setValue(0)
            self.bonus_check.setChecked(False)
            self.venue_size_combo.setCurrentIndex(0)
            self.venue_combo.setCurrentText("")
            self.completion_mode_combo.setCurrentIndex(0)
            self.text_edit.clear()
            self.completion_bonus_combo.setCurrentIndex(0)
            self.bonus_text_edit.clear()
            self.media_label.setText("(none)")
            self.media_clear_btn.setEnabled(False)
        self._block_signals(False)

    def _commit(self):
        if 0 <= self._index < len(self._tiers):
            t = self._tiers[self._index]
            t["name"] = self.name_edit.text().strip()
            t["description"] = self.description_edit.text().strip() or None
            t["song_count"] = int(self.songs_spin.value())
            t["unlock_type"] = self.unlock_type_combo.currentText()
            t["unlock_criteria"] = int(self.unlock_spin.value())
            t["is_bonus"] = self.bonus_check.isChecked()
            t["venue_size"] = self.venue_size_combo.currentText()
            t["venue_hint"] = self.venue_combo.currentText().strip() or None
            t["completion_mode"] = self.completion_mode_combo.currentText()
            t["custom_unlock_text"] = self.text_edit.toPlainText().strip() or None
            t["completion_bonus"] = self.completion_bonus_combo.currentText()
            t["completion_bonus_text"] = self.bonus_text_edit.text().strip() or None

    def _block_signals(self, blocked):
        for w in self._detail_widgets():
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

    def _on_choose_media(self):
        self._commit()
        if not (0 <= self._index < len(self._tiers)):
            return
        bonus = self.completion_bonus_combo.currentText()
        filters = MEDIA_FILTERS.get(bonus, MEDIA_FILTERS["Image"])
        filters += ";;All files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Choose completion-bonus media", "", filters)
        if not path:
            return
        try:
            os.makedirs(self._media_dir, exist_ok=True)
            dest = os.path.join(str(self._media_dir), os.path.basename(path))
            shutil.copyfile(path, dest)
        except OSError as exc:
            QMessageBox.warning(self, "Copy failed", f"Could not copy media file:\n{exc}")
            return
        self._tiers[self._index]["media_path"] = dest
        self._load_detail()
        self.changed.emit()

    def _on_clear_media(self):
        if 0 <= self._index < len(self._tiers):
            path = self._tiers[self._index].get("media_path")
            self._tiers[self._index]["media_path"] = None
            if path and _is_managed_media(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
            self._load_detail()
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
