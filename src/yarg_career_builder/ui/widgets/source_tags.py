"""Tag-style multi-select for music sources (dropdown + removable chips)."""

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class FlowLayout(QLayout):
    """A wrapping layout that flows child widgets left-to-right, top-to-bottom."""

    def __init__(self, parent=None, margin=0, spacing=6):
        super().__init__(parent)
        self._items = []
        self._margin = margin
        self._spacing = spacing
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientations()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        x = rect.x() + m.left()
        y = rect.y() + m.top()
        right = rect.right() - m.right()
        line_height = 0
        space_x = self.spacing()
        space_y = self.spacing()

        for item in self._items:
            w = item.widget()
            hint = w.sizeHint()
            next_x = x + hint.width() + space_x
            if next_x - space_x > right and line_height > 0:
                x = rect.x() + m.left()
                y = y + line_height + space_y
                next_x = x + hint.width() + space_x
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())

        return y + line_height - rect.y() + m.bottom()


class SourceTagSelector(QWidget):
    """Filterable dropdown + removable source chips.

    Emits ``changed`` whenever the set of selected sources (or a weight) changes.
    """

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        self._selected = {}  # source id -> weight
        self._weights_visible = False

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter by name or source id…")
        self.filter_edit.setToolTip("Filter the list of available sources by name or source id.")
        self.filter_edit.textChanged.connect(self._rebuild_dropdown)

        self.type_combo = QComboBox()
        self.type_combo.setToolTip("Filter available sources by type.")
        self.type_combo.currentIndexChanged.connect(self._rebuild_dropdown)

        self.public_only = QCheckBox("Public-allowed only")
        self.public_only.setToolTip("Only show sources that are allowed in a public career.")
        self.public_only.toggled.connect(self._rebuild_dropdown)

        filter_row = QHBoxLayout()
        filter_row.addWidget(self.filter_edit, 1)
        filter_row.addWidget(self.type_combo)
        filter_row.addWidget(self.public_only)

        self.source_combo = QComboBox()
        self.source_combo.setMinimumWidth(260)
        self.source_combo.setToolTip("Pick a music source to add to the career.")

        self.add_button = QPushButton("Add")
        self.add_button.setToolTip("Add the selected source as a tag.")
        self.add_button.clicked.connect(self._add_current)

        add_row = QHBoxLayout()
        add_row.addWidget(self.source_combo, 1)
        add_row.addWidget(self.add_button)

        self.chips_widget = QWidget()
        self.chips_layout = FlowLayout(self.chips_widget, margin=0, spacing=6)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addLayout(filter_row)
        layout.addLayout(add_row)
        layout.addWidget(self.chips_widget, 1)

        self._rebuild_dropdown()
        self._rebuild_chips()

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def set_sources(self, rows, selected):
        """Set available rows and the current selection.

        rows: list of {source, name, type, count, public}.
        selected: dict of source id -> weight for sources to pre-select.
        """
        self._rows = list(rows)
        self._selected = dict(selected)
        self._rebuild_type_combo()
        self._rebuild_dropdown()
        self._rebuild_chips()

    def set_weights_visible(self, visible):
        self._weights_visible = bool(visible)
        self._rebuild_chips()

    def selected_ids(self):
        return list(self._selected.keys())

    def weights(self):
        return dict(self._selected)

    # ------------------------------------------------------------------ #
    #  Internals
    # ------------------------------------------------------------------ #

    def _rebuild_type_combo(self):
        types = sorted({r["type"] for r in self._rows if r["type"] and r["type"] != "?"})
        current = self.type_combo.currentData()
        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        self.type_combo.addItem("All types", None)
        for t in types:
            self.type_combo.addItem(t, t)
        idx = self.type_combo.findData(current)
        self.type_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.type_combo.blockSignals(False)

    def _rebuild_dropdown(self):
        text = self.filter_edit.text().strip().lower()
        typ = self.type_combo.currentData()
        public_only = self.public_only.isChecked()

        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        for r in self._rows:
            if r["source"] in self._selected:
                continue
            if text and text not in r["source"].lower() and text not in r["name"].lower():
                continue
            if typ and r["type"] != typ:
                continue
            if public_only and not r["public"]:
                continue
            self.source_combo.addItem(f"{r['name']}  ({r['count']} songs)", r["source"])
        self.source_combo.blockSignals(False)

        has_items = self.source_combo.count() > 0
        self.source_combo.setEnabled(has_items)
        self.add_button.setEnabled(has_items)

    def _rebuild_chips(self):
        while self.chips_layout.count():
            item = self.chips_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        if not self._selected:
            empty = QLabel("No sources selected — add some from the dropdown above.")
            empty.setProperty("muted", True)
            self.chips_layout.addWidget(empty)
            return

        for sid, weight in self._selected.items():
            self.chips_layout.addWidget(self._make_chip(sid, weight))

    def _make_chip(self, sid, weight):
        info = next((r for r in self._rows if r["source"] == sid), None)
        name = info["name"] if info else sid
        count = info["count"] if info else 0
        typ = info["type"] if info else "?"
        public = info["public"] if info else False

        tooltip = (
            f"{name}\n"
            f"Source id: {sid}\n"
            f"Type: {typ}\n"
            f"Songs in library: {count}\n"
            f"{'Public-allowed' if public else 'Not public-allowed'}"
        )

        chip = QFrame()
        chip.setProperty("tag", True)
        chip.setToolTip(tooltip)

        lay = QHBoxLayout(chip)
        lay.setContentsMargins(10, 2, 6, 2)
        lay.setSpacing(6)

        label = QLabel(name)
        label.setToolTip(tooltip)
        lay.addWidget(label)

        if self._weights_visible:
            spin = QSpinBox()
            spin.setRange(1, 1000)
            spin.setValue(int(weight))
            spin.setFixedWidth(60)
            spin.setToolTip("Relative weight — higher means more songs are pulled from this source.")
            spin.valueChanged.connect(lambda v, s=sid: self._set_weight(s, v))
            lay.addWidget(spin)

        close_btn = QPushButton("×")
        close_btn.setFixedWidth(22)
        close_btn.setProperty("chipClose", True)
        close_btn.setToolTip(f"Remove {name}")
        close_btn.clicked.connect(lambda checked=False, s=sid: self._remove(s))
        lay.addWidget(close_btn)

        return chip

    def _add_current(self):
        sid = self.source_combo.currentData()
        if sid is None:
            return
        self._selected[sid] = self._selected.get(sid, 1)
        self._rebuild_dropdown()
        self._rebuild_chips()
        self.changed.emit()

    def _remove(self, sid):
        self._selected.pop(sid, None)
        self._rebuild_dropdown()
        self._rebuild_chips()
        self.changed.emit()

    def _set_weight(self, sid, value):
        self._selected[sid] = int(value)
        self.changed.emit()
