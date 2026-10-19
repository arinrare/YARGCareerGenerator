"""Main application window."""

import os
import uuid
from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..paths import SETTINGS_PATH, SOURCES_PATH, CAREERS_DIR, BASE, BUNDLED_TEMPLATE_PATH, media_dir_for
from ..core.config import save_settings
from ..core.bootstrap import load_app_state
from ..core.career_io import (
    load_career_file,
    load_template,
    import_template,
    reconcile_media,
    scan_careers,
    delete_career,
    clean_unused_media,
)
from ..core.generate import sanitize_filename
from ..core.pipeline import (
    scan_report,
    build_career,
    regenerate_sources,
    update_setlist,
    save_setlist,
    PublicBlockError,
)
from ..core.sources import find_yarg_installs, source_info, merged_source_rows
from .widgets.path_picker import PathPicker
from .widgets.log_panel import LogPanel
from .widgets.source_tags import SourceTagSelector
from .widgets.tier_editor import TierEditor
from .widgets.controls import NoScrollComboBox, NoScrollSpinBox
from .workers import Worker
from .dialogs.about import AboutDialog

DIFFICULTY_FIELDS = ["diff_guitar", "diff_band", "diff_drums", "diff_vocals", "diff_bass", "diff_keys"]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YARG Career Builder")
        self.resize(1020, 760)
        self.setMinimumSize(640, 480)

        self.settings, self.sources = load_app_state(apply_startup=True)
        counts = self.settings.get("scan_counts") or {}
        self.scan_cache = {"counts": counts} if counts else None
        self._workers = []
        self._dark = True
        self._career_dirty = False
        self._setlist_dirty = False

        self._build_menus()
        self._build_ui()
        self._load_settings_into_ui()

        self.log_panel.log("Ready. Set your paths, scan your library, then build.")

    # ------------------------------------------------------------------ #
    #  Construction
    # ------------------------------------------------------------------ #

    def _build_menus(self):
        file_menu = self.menuBar().addMenu("&File")

        load_career = file_menu.addAction("&Load Career…")
        load_career.triggered.connect(self.on_load_career)
        import_tpl = file_menu.addAction("&Import Template…")
        import_tpl.triggered.connect(self.on_import_template)
        reset_tpl = file_menu.addAction("&Reset to Template")
        reset_tpl.triggered.connect(self.on_reset_to_template)
        file_menu.addSeparator()

        open_output = file_menu.addAction("Open &Output Folder")
        open_output.triggered.connect(self.on_open_output_folder)
        file_menu.addSeparator()
        exit_act = file_menu.addAction("E&xit")
        exit_act.triggered.connect(self.close)

        view_menu = self.menuBar().addMenu("&View")
        theme_act = view_menu.addAction("Toggle &Theme")
        theme_act.triggered.connect(self.on_toggle_theme)
        view_menu.addSeparator()
        refresh_act = view_menu.addAction("&Refresh Library Scan")
        refresh_act.triggered.connect(self.on_scan)

        settings_menu = self.menuBar().addMenu("&Settings")
        open_settings = settings_menu.addAction("Open &settings.json")
        open_settings.triggered.connect(self.on_open_settings_json)
        open_sources = settings_menu.addAction("Open &sources.json")
        open_sources.triggered.connect(lambda: os.startfile(str(SOURCES_PATH)))
        settings_menu.addSeparator()
        regen = settings_menu.addAction("&Regenerate Sources…")
        regen.triggered.connect(self.on_regenerate_sources)

        help_menu = self.menuBar().addMenu("&Help")
        about = help_menu.addAction("&About")
        about.triggered.connect(self.on_about)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ---- Paths -----------------------------------------------------
        paths_group = QGroupBox("Paths")
        paths_layout = QVBoxLayout(paths_group)

        yarg_row = QHBoxLayout()
        self.yarg_picker = PathPicker(
            "YARG install folder (contains YARG.exe)",
            mode="folder",
            hint="The YARG install folder that contains YARG.exe. Used to regenerate the source registry.",
        )
        self.auto_detect_btn = QPushButton("Auto-detect")
        self.auto_detect_btn.setToolTip("Search all drives for a YARG install.")
        self.auto_detect_btn.clicked.connect(self.on_auto_detect_yarg)
        yarg_row.addWidget(self.yarg_picker, 1)
        yarg_row.addWidget(self.auto_detect_btn)

        self.music_picker = PathPicker(
            "Music library folder",
            mode="folder",
            hint="Folder scanned for song folders (each containing a song.ini).",
        )
        self.output_picker = PathPicker(
            "Output folder (blank = app's 'careers' folder)",
            mode="folder",
            hint="Where the built .json and .preset career files are written. Leave blank to write into the app's 'careers' folder.",
        )

        paths_layout.addLayout(yarg_row)
        paths_layout.addWidget(self.music_picker)
        paths_layout.addWidget(self.output_picker)

        # ---- Actions ---------------------------------------------------
        action_row = QHBoxLayout()
        self.scan_btn = QPushButton("Scan Library")
        self.scan_btn.setToolTip("Scan the music library and count songs per source.")
        self.scan_btn.clicked.connect(self.on_scan)
        self.regen_btn = QPushButton("Regenerate Sources")
        self.regen_btn.setToolTip("Rebuild sources.json from a YARG install's OpenSource registry.")
        self.regen_btn.clicked.connect(self.on_regenerate_sources)
        self.load_btn = QPushButton("Load Career")
        self.load_btn.setProperty("accent", True)
        self.load_btn.setToolTip("Load an existing career's structure and metadata.")
        self.load_btn.clicked.connect(self.on_load_career)
        self.reset_default_btn = QPushButton("Reset to Default")
        self.reset_default_btn.setToolTip("Reset the career to the shipped default.")
        self.reset_default_btn.clicked.connect(self.on_reset_to_default)
        self.build_btn = QPushButton("Build Career")
        self.build_btn.setProperty("accent", True)
        self.build_btn.setToolTip("Build the career and write .json + .preset files.")
        self.build_btn.clicked.connect(self.on_build)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(140)
        self.progress.hide()

        action_row.addWidget(self.scan_btn)
        action_row.addWidget(self.regen_btn)
        action_row.addStretch(1)
        action_row.addWidget(self.progress)
        action_row.addWidget(self.load_btn)
        action_row.addWidget(self.reset_default_btn)
        action_row.addWidget(self.build_btn)

        # ---- Tabs ------------------------------------------------------
        self.tab_widget = QTabWidget()
        self._build_career_tab()
        self._build_tiers_tab()
        self._build_songs_tab()
        self._build_careers_tab()

        # ---- Scrollable content (paths + actions + tabs) ---------------
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(10)
        scroll_layout.addWidget(paths_group)
        scroll_layout.addLayout(action_row)
        scroll_layout.addWidget(self.tab_widget)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidget(scroll_content)

        # ---- Log -------------------------------------------------------
        self.log_panel = LogPanel()

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.scroll_area)
        splitter.addWidget(self.log_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([520, 160])

        root.addWidget(splitter, 1)

        self.statusBar().showMessage("Ready")

    def _build_career_tab(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # ---- Career metadata -------------------------------------------
        form_group = QGroupBox("Career")
        form = QFormLayout(form_group)
        form.setLabelAlignment(Qt.AlignRight)

        self.name_edit = QLineEdit()
        self.title_edit = QLineEdit()
        self.description_edit = QPlainTextEdit()
        self.description_edit.setFixedHeight(64)
        self.version_spin = NoScrollSpinBox()
        self.version_spin.setRange(1, 9999)
        self.type_edit = QLineEdit()

        for w, sig in (
            (self.name_edit, self.name_edit.textChanged),
            (self.title_edit, self.title_edit.textChanged),
            (self.description_edit, self.description_edit.textChanged),
            (self.version_spin, self.version_spin.valueChanged),
            (self.type_edit, self.type_edit.textChanged),
        ):
            sig.connect(self._mark_career_dirty)


        self._add_form_row(
            form, "Name", self.name_edit,
            "The career's name — shown in YARG's career list and used as the output file name (e.g. \"My Tour\").",
        )
        self._add_form_row(
            form, "Title", self.title_edit,
            "Optional short display title. Usually left blank; the Name is used instead.",
        )
        self._add_form_row(
            form, "Description", self.description_edit,
            "Flavour text shown when the career is opened in YARG.",
        )
        self._add_form_row(
            form, "Version", self.version_spin,
            "Preset version number. Leave at 1 unless you track your own versions.",
        )
        self._add_form_row(
            form, "Type", self.type_edit,
            "Preset type. Always \"Career\".",
        )

        # ---- Sources ---------------------------------------------------
        sources_group = QGroupBox("Sources")
        sources_layout = QVBoxLayout(sources_group)

        self.source_tags = SourceTagSelector()
        self.source_tags.changed.connect(self._update_source_summary)
        sources_layout.addWidget(self.source_tags)

        mode_row = QHBoxLayout()
        mode_label = QLabel("Selection mode:")
        mode_label.setToolTip(
            "Filter/limit — use exactly the sources you add.\n"
            "Weighted — split the career across sources in proportion to each weight."
        )
        mode_row.addWidget(mode_label)
        self.mode_combo = NoScrollComboBox()
        self.mode_combo.addItem("Filter / limit (pick sources)", "filter")
        self.mode_combo.addItem("Weighted (set source proportions)", "weighted")
        self.mode_combo.setToolTip(
            "Filter: use exactly the sources you add (optionally capped to the top N).\n"
            "Weighted: split the career across sources in proportion to each source's weight."
        )
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_combo)

        mode_row.addSpacing(16)
        limit_label = QLabel("Source limit:")
        limit_label.setToolTip(
            "Cap the number of distinct sources used (0 = unlimited). "
            "Sources are ranked by song count; the top N are kept."
        )
        mode_row.addWidget(limit_label)
        self.limit_spin = NoScrollSpinBox()
        self.limit_spin.setRange(0, 10000)
        self.limit_spin.setSpecialValueText("unlimited")
        self.limit_spin.setToolTip(
            "Cap the number of distinct sources used (0 = unlimited). "
            "Sources are ranked by song count; the top N are kept."
        )
        mode_row.addWidget(self.limit_spin)

        mode_row.addStretch(1)
        self.source_summary = QLabel()
        self.source_summary.setProperty("muted", True)
        mode_row.addWidget(self.source_summary)

        sources_layout.addLayout(mode_row)

        # ---- Build rules -----------------------------------------------
        rules_group = QGroupBox("Build rules")
        rules = QFormLayout(rules_group)
        rules.setLabelAlignment(Qt.AlignRight)

        self.visibility_combo = NoScrollComboBox()
        self.visibility_combo.addItems(["private", "public"])

        self.difficulty_combo = NoScrollComboBox()
        self.difficulty_combo.addItems(DIFFICULTY_FIELDS)

        self.ascending_check = QCheckBox("Sort easiest first")

        self.missing_combo = NoScrollComboBox()
        self.missing_combo.addItem("last (keep songs without difficulty)", "last")
        self.missing_combo.addItem("skip (drop songs without difficulty)", "skip")

        self._add_form_row(
            rules, "Visibility", self.visibility_combo,
            "private — any source is allowed.\n"
            "public — the build is blocked if any selected source is a Guitar Hero / "
            "Rock Band / other-game setlist.",
        )
        self._add_form_row(
            rules, "Difficulty field", self.difficulty_combo,
            "Which song.ini value orders songs from easiest to hardest (e.g. diff_guitar).",
        )
        self._add_form_row(
            rules, "Order", self.ascending_check,
            "Sort direction — easiest first (checked) or hardest first (unchecked).",
        )
        self._add_form_row(
            rules, "Missing difficulty", self.missing_combo,
            "What to do with songs that have no difficulty value: keep them at the end, or drop them.",
        )

        layout.addWidget(form_group)
        layout.addWidget(sources_group)
        layout.addWidget(rules_group)
        layout.addStretch(1)

        self.tab_widget.addTab(content, "Career")

    @staticmethod
    def _add_form_row(form, label_text, widget, tooltip):
        """Add a form row and attach the tooltip to both the field and its label."""
        form.addRow(label_text, widget)
        widget.setToolTip(tooltip)
        label = form.labelForField(widget)
        if label is not None:
            label.setToolTip(tooltip)

    def _build_tiers_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        header = QHBoxLayout()
        hint = QLabel(
            "Edit the career structure. Add, remove, reorder, or edit tiers."
        )
        hint.setProperty("muted", True)
        header.addWidget(hint, 1)
        self.update_setlist_btn = QPushButton("Fill setlist")
        self.update_setlist_btn.setProperty("accent", True)
        self.update_setlist_btn.setToolTip(
            "Reconcile the setlist with the current tiers, filling any new slots from the library."
        )
        self.update_setlist_btn.setEnabled(False)
        self.update_setlist_btn.clicked.connect(self.on_update_setlist)
        header.addWidget(self.update_setlist_btn)
        layout.addLayout(header)

        self.tier_editor = TierEditor()
        self.tier_editor.changed.connect(self._update_source_summary)
        self.tier_editor.changed.connect(self._mark_career_dirty)
        self.tier_editor.changed.connect(self._on_tiers_changed)
        layout.addWidget(self.tier_editor, 1)

        self.tab_widget.addTab(tab, "Tiers")

    def _build_songs_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        hint = QLabel("Read-only view of the current career. Songs are listed under each tier.")
        hint.setProperty("muted", True)
        header.addWidget(hint, 1)
        self.save_setlist_btn = QPushButton("Save setlist")
        self.save_setlist_btn.setProperty("accent", True)
        self.save_setlist_btn.setToolTip(
            "Save the current setlist to a .preset and .json in the careers folder."
        )
        self.save_setlist_btn.clicked.connect(self.on_save_setlist)
        header.addWidget(self.save_setlist_btn)
        layout.addLayout(header)

        self.setlist_tree = QTreeWidget()
        self.setlist_tree.setColumnCount(4)
        self.setlist_tree.setHeaderLabels(["Title", "Artist", "Charter", "Source"])
        self.setlist_tree.setEditTriggers(QTreeWidget.NoEditTriggers)
        self.setlist_tree.header().setStretchLastSection(False)
        self.setlist_tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        layout.addWidget(self.setlist_tree)

        self.tab_widget.addTab(tab, "Setlist")

    def _build_careers_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        hint = QLabel("Careers in the output folder. Delete removes its files and, if unused, its media.")
        hint.setProperty("muted", True)
        header.addWidget(hint, 1)

        self.careers_refresh_btn = QPushButton("Refresh")
        self.careers_refresh_btn.setToolTip("Re-scan the output folder for careers.")
        self.careers_refresh_btn.clicked.connect(self._refresh_careers)

        self.careers_load_btn = QPushButton("Load")
        self.careers_load_btn.setToolTip("Load the selected career into the editor.")
        self.careers_load_btn.clicked.connect(self._on_load_career_from_list)

        self.careers_delete_btn = QPushButton("Delete")
        self.careers_delete_btn.setToolTip("Delete the selected career's .json/.preset and, if unused, its media.")
        self.careers_delete_btn.clicked.connect(self._on_delete_career)

        self.careers_clean_btn = QPushButton("Clean unused media")
        self.careers_clean_btn.setToolTip("Delete media folders for careers that no longer exist in the output folder.")
        self.careers_clean_btn.clicked.connect(self._on_clean_unused_media)

        for b in (self.careers_refresh_btn, self.careers_load_btn, self.careers_delete_btn, self.careers_clean_btn):
            header.addWidget(b)
        layout.addLayout(header)

        self.careers_list = QTreeWidget()
        self.careers_list.setColumnCount(4)
        self.careers_list.setHeaderLabels(["Name", "Files", "Tiers", "Media"])
        self.careers_list.setRootIsDecorated(False)
        self.careers_list.setSelectionBehavior(QTreeWidget.SelectRows)
        self.careers_list.setEditTriggers(QTreeWidget.NoEditTriggers)
        self.careers_list.header().setStretchLastSection(False)
        self.careers_list.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.careers_list.itemDoubleClicked.connect(lambda *_: self._on_load_career_from_list())
        layout.addWidget(self.careers_list)

        self.tab_widget.addTab(tab, "Careers")

    # ------------------------------------------------------------------ #
    #  Settings <-> UI
    # ------------------------------------------------------------------ #

    def _load_settings_into_ui(self):
        s = self.settings

        yarg = s.get("yarg", {}) or {}
        self.yarg_picker.setText(yarg.get("install_dir", "") or "")
        self.music_picker.setText(s.get("music_root", "") or "")
        self.output_picker.setText(s.get("output_dir", "") or "")

        career = s.get("career", {}) or {}
        self.name_edit.setText(career.get("name") or "")
        self.title_edit.setText(career.get("title") or "")
        self.description_edit.setPlainText(career.get("description") or "")
        self.version_spin.setValue(int(career.get("version") or 1))
        self.type_edit.setText(career.get("type") or "Career")

        self.visibility_combo.setCurrentText(s.get("visibility", "private"))

        diff = s.get("difficulty", {}) or {}
        field = diff.get("field", "diff_guitar")
        if field in DIFFICULTY_FIELDS:
            self.difficulty_combo.setCurrentText(field)
        self.ascending_check.setChecked(bool(diff.get("ascending", True)))
        missing = diff.get("missing", "last")
        idx = self.missing_combo.findData(missing)
        self.missing_combo.setCurrentIndex(idx if idx >= 0 else 0)

        sel = s.get("source_selection", {}) or {}
        weights = sel.get("weights") or {}
        limit = int(sel.get("limit") or 0)

        if weights:
            self.mode_combo.setCurrentIndex(1)  # weighted
            self.limit_spin.setValue(0)
        else:
            self.mode_combo.setCurrentIndex(0)  # filter
            self.limit_spin.setValue(limit)
        self._on_mode_changed()

        self.tier_editor.set_tiers(s.get("tiers", []))
        self.tier_editor.set_media_dir(media_dir_for(s.get("career", {})))

        self._refresh_sources()
        self._refresh_setlist()
        self._refresh_careers()
        self._career_dirty = False

    def _collect_settings_from_ui(self):
        s = deepcopy(self.settings)

        s.setdefault("yarg", {})["install_dir"] = self.yarg_picker.text()
        s["music_root"] = self.music_picker.text()
        s["output_dir"] = self.output_picker.text()

        career = s.setdefault("career", {})
        career["name"] = self.name_edit.text().strip()
        career["title"] = self.title_edit.text().strip() or None
        career["description"] = self.description_edit.toPlainText().strip() or None
        career.setdefault("source", "yarg")
        career["version"] = int(self.version_spin.value())
        career["type"] = self.type_edit.text().strip() or "Career"
        career.setdefault("id", str(uuid.uuid4()))

        s["visibility"] = self.visibility_combo.currentText()

        diff = s.setdefault("difficulty", {})
        diff["field"] = self.difficulty_combo.currentText()
        diff["ascending"] = self.ascending_check.isChecked()
        diff["missing"] = self.missing_combo.currentData()

        sel = s.setdefault("source_selection", {})
        if self.mode_combo.currentData() == "weighted":
            sel["weights"] = self.source_tags.weights()
            sel["filter"] = []
            sel["limit"] = 0
        else:
            sel["filter"] = self.source_tags.selected_ids()
            sel["limit"] = int(self.limit_spin.value())
            sel["weights"] = {}

        s["tiers"] = self.tier_editor.tiers()

        return s

    def _persist_settings(self):
        self.settings = self._collect_settings_from_ui()
        save_settings(self.settings)
        reconcile_media(self.settings.get("career", {}), self.settings.get("tiers", []))

    def _mark_career_dirty(self, *args):
        self._career_dirty = True

    def _confirm_discard_edits(self):
        if not self._career_dirty:
            return True
        reply = QMessageBox.question(
            self, "Discard career edits?",
            "You have unsaved career changes. This will replace the current "
            "structure and lose those edits.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    def _refresh_sources(self):
        pc = self.settings.get("public_checks", {}) or {}
        allowed_types = pc.get("allowed_types", [])
        always_allowed = pc.get("always_allowed_ids", [])

        counts = (self.scan_cache or {}).get("counts", {})
        rows = [
            r for r in merged_source_rows(self.sources, counts, allowed_types, always_allowed)
            if r["count"] > 0
        ]

        sel = self.settings.get("source_selection", {}) or {}
        weights = sel.get("weights") or {}
        filter_list = sel.get("filter") or []
        if weights:
            selected = {k: int(v) for k, v in weights.items() if v}
        else:
            selected = {s: 1 for s in filter_list}

        self.source_tags.set_has_counts(bool(counts))
        self.source_tags.set_sources(rows, selected)
        self._update_source_summary()

    def _on_mode_changed(self):
        weighted = self.mode_combo.currentData() == "weighted"
        self.source_tags.set_weights_visible(weighted)
        self.limit_spin.setEnabled(not weighted)

    def _update_source_summary(self):
        ids = self.source_tags.selected_ids()
        counts = (self.scan_cache or {}).get("counts", {})
        target = sum(t["song_count"] for t in self.tier_editor.tiers())
        total = sum(counts.get(i, 0) for i in ids)

        if self.scan_cache is None:
            self.source_summary.setText(
                f"{len(ids)} source(s) selected (scan to see song counts) · target {target}"
            )
        else:
            self.source_summary.setText(
                f"{len(ids)} source(s) selected · {total} songs · target {target}"
            )

    # ------------------------------------------------------------------ #
    #  Setlist
    # ------------------------------------------------------------------ #

    def _refresh_setlist(self):
        self.setlist_tree.clear()
        setlist = self.settings.get("setlist") or {}
        tiers = self.settings.get("tiers", [])

        for i, tier in enumerate(tiers):
            name = tier.get("name") or "Untitled tier"
            songs = setlist.get(tier.get("id"), [])
            header = QTreeWidgetItem([f"{i + 1}. {name}", f"{len(songs)} songs", "", ""])
            font = header.font(0)
            font.setBold(True)
            header.setFont(0, font)
            self.setlist_tree.addTopLevelItem(header)
            for song in songs:
                item = QTreeWidgetItem([
                    song.get("title", ""),
                    song.get("artist", ""),
                    song.get("charter", ""),
                    song.get("source", ""),
                ])
                header.addChild(item)
            header.setExpanded(True)

    def _on_tiers_changed(self, *args):
        self._setlist_dirty = True
        self.update_setlist_btn.setEnabled(True)

    def on_update_setlist(self):
        self._persist_settings()
        old_setlist = self.settings.get("setlist") or {}
        self.log_panel.log("Updating setlist…")
        self._start_worker(
            update_setlist, self._on_update_setlist_done,
            self.settings, self.sources, old_setlist,
        )

    def _on_update_setlist_done(self, new_setlist):
        self.settings["setlist"] = new_setlist
        save_settings(self.settings)
        self._setlist_dirty = False
        self.update_setlist_btn.setEnabled(False)
        self._refresh_setlist()
        self.log_panel.log("Setlist updated.")

    # ------------------------------------------------------------------ #
    #  Career management
    # ------------------------------------------------------------------ #

    def _careers_out_dir(self):
        return str(self.settings.get("output_dir") or CAREERS_DIR)

    def _refresh_careers(self):
        records = scan_careers(self._careers_out_dir())
        loaded = self.settings.get("loaded_career") or ""
        loaded_stem = os.path.splitext(loaded)[0] if loaded else None

        self.careers_list.clear()
        for r in records:
            files = []
            if r["json"]:
                files.append(".json")
            if r["preset"]:
                files.append(".preset")
            files_text = " + ".join(files) if files else "—"
            media_text = "yes" if r["has_media"] else "—"
            name = r["name"]
            if r["stem"] == loaded_stem:
                name += "  (loaded)"
            item = QTreeWidgetItem([name, files_text, str(r["tier_count"]), media_text])
            item.setData(0, Qt.UserRole, r["stem"])
            self.careers_list.addTopLevelItem(item)

    def _selected_career_stem(self):
        items = self.careers_list.selectedItems()
        return items[0].data(0, Qt.UserRole) if items else None

    def _on_load_career_from_list(self):
        stem = self._selected_career_stem()
        if not stem:
            QMessageBox.information(self, "Select a career", "Select a career to load.")
            return
        out_dir = self._careers_out_dir()
        preset = os.path.join(out_dir, f"{stem}.preset")
        jsonp = os.path.join(out_dir, f"{stem}.json")
        path = preset if os.path.isfile(preset) else (jsonp if os.path.isfile(jsonp) else None)
        if not path:
            QMessageBox.warning(self, "Not found", f"No career files for '{stem}'.")
            return
        if not self._confirm_discard_edits():
            return
        try:
            result = load_career_file(path)
        except Exception as exc:
            QMessageBox.critical(self, "Load failed", f"Could not load career:\n{exc}")
            return
        self._apply_structure(result, os.path.basename(path))
        self.log_panel.log(f"Loaded career: {os.path.basename(path)}")
        self._refresh_careers()

    def _on_delete_career(self):
        stem = self._selected_career_stem()
        if not stem:
            QMessageBox.information(self, "Select a career", "Select a career to delete.")
            return
        loaded = self.settings.get("loaded_career") or ""
        is_loaded = stem == (os.path.splitext(loaded)[0] if loaded else None)

        msg = (f"Delete career '{stem}'?\n\n"
               "This removes its .json/.preset files and, if no other career uses it, its media.")
        if is_loaded:
            msg += "\n\nThis is the currently loaded career — the active structure will reset to the template."
        reply = QMessageBox.question(self, "Delete career", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        result = delete_career(self._careers_out_dir(), stem)
        for f in result["files"]:
            self.log_panel.log(f"Deleted {f}")
        if result.get("media"):
            self.log_panel.log(f"Deleted media {result['media']}")

        if is_loaded:
            self.settings["loaded_career"] = None
            try:
                tpl = load_template()
            except Exception:
                tpl = None
            if tpl:
                self._apply_structure(tpl, None)
            self.log_panel.log("Loaded career deleted; reset to template.")
        self._refresh_careers()

    def _on_clean_unused_media(self):
        reply = QMessageBox.question(
            self, "Clean unused media",
            "Remove media folders for careers that no longer exist in the output folder?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        removed = clean_unused_media(self._careers_out_dir())
        if removed:
            for d in removed:
                self.log_panel.log(f"Removed unused media {d}")
        else:
            self.log_panel.log("No unused media found.")
        self._refresh_careers()

    # ------------------------------------------------------------------ #
    #  Actions
    # ------------------------------------------------------------------ #

    def _start_worker(self, fn, on_result, *args):
        worker = Worker(fn, *args)
        worker.result.connect(on_result)
        worker.error.connect(self._on_worker_error)
        worker.finished.connect(lambda: self._finish_work(worker))
        self._workers.append(worker)
        self._set_busy(True)
        worker.start()

    def _set_busy(self, busy):
        self.scan_btn.setEnabled(not busy)
        self.regen_btn.setEnabled(not busy)
        self.load_btn.setEnabled(not busy)
        self.reset_default_btn.setEnabled(not busy)
        self.build_btn.setEnabled(not busy)
        self.save_setlist_btn.setEnabled(not busy)
        self.progress.setVisible(busy)
        if busy:
            self.statusBar().showMessage("Working…")
        else:
            self.statusBar().showMessage("Ready")

    def _finish_work(self, worker):
        self._workers = [w for w in self._workers if w is not worker]
        if not self._workers:
            self._set_busy(False)

    def _on_worker_error(self, exc):
        self.log_panel.log("")
        if isinstance(exc, PublicBlockError):
            self.log_panel.log("PUBLIC CAREER BLOCKED — the following sources are not allowed:")
            for src, titles in sorted(exc.violations.items()):
                info = source_info(self.sources, src)
                label = info["name"] if info else "unknown"
                self.log_panel.log(f"  - {src} ({label}): {len(titles)} song(s)")
            self.log_panel.log("Set visibility to 'private' or restrict the selected sources.")
            QMessageBox.warning(self, "Public career blocked",
                                "The selected sources are not allowed in a public career.\n"
                                "See the log for details.")
        else:
            self.log_panel.log(f"Error: {exc}")
            QMessageBox.critical(self, "Error", str(exc))

    def on_scan(self):
        self._persist_settings()
        self.log_panel.log(f"Scanning {self.settings.get('music_root')} …")
        self._start_worker(scan_report, self._on_scan_done, self.settings, self.sources)

    def _on_scan_done(self, report):
        self.scan_cache = report
        self.settings["scan_counts"] = report["counts"]
        save_settings(self.settings)
        self.log_panel.log(
            f"Found {len(report['songs'])} song folders "
            f"({report['no_source']} without a source icon)."
        )
        self.log_panel.log(
            f"Career target: {report['target']} songs across {report['tier_count']} tiers.\n"
        )
        for row in report["rows"]:
            self.log_panel.log(
                f"  {row['source']:<14} {row['type']:<7} {row['count']:>5}  "
                f"{'public' if row['public'] else 'private':<8} {row['name']}"
            )
        self._refresh_sources()

    def on_build(self):
        self._persist_settings()
        self.log_panel.log("Building career…")
        self._start_worker(build_career, self._on_build_done, self.settings, self.sources)

    def _on_build_done(self, result):
        name = result["career"].get("name") or "Career"
        self.log_panel.log(
            f"\nBuilt '{name}' with {len(result['selected'])} songs "
            f"across {len(result['filled'])} tiers."
        )
        self.log_panel.log("Per source:")
        for src, n in sorted(result["breakdown"].items(), key=lambda kv: -kv[1]):
            info = source_info(self.sources, src)
            label = info["name"] if info else "?"
            self.log_panel.log(f"  - {src:<14} {n:>4} songs   ({label})")
        for cfg, chunk in result["filled"]:
            self.log_panel.log(f"  - {cfg['name']:<26} {len(chunk)} songs")
        self.log_panel.log(f"\nWrote:\n  {result['json_path']}\n  {result['preset_path']}")
        self.statusBar().showMessage(f"Built '{name}'")

        self.settings["loaded_career"] = os.path.basename(result["json_path"])
        self.settings["setlist"] = {
            cfg["id"]: [
                {
                    "artist": s["artist"],
                    "title": s["title"],
                    "charter": s["charter"],
                    "source": s["source"],
                }
                for s in chunk
            ]
            for cfg, chunk in result["filled"]
        }
        save_settings(self.settings)
        self._career_dirty = False
        self._setlist_dirty = False
        self.update_setlist_btn.setEnabled(False)
        self._refresh_setlist()
        self._refresh_careers()

        reply = QMessageBox.question(
            self, "Build complete",
            f"Built '{name}' with {len(result['selected'])} songs.\n\n"
            "Open the output folder?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._open_path(os.path.dirname(result["json_path"]))

    def on_auto_detect_yarg(self):
        self.log_panel.log("Searching for YARG installs…")
        installs = find_yarg_installs()
        if not installs:
            self.log_panel.log("No YARG install found automatically.")
            self.yarg_picker.edit.setFocus()
            return
        chosen = installs[0]
        if len(installs) > 1:
            labels = [
                f"{i['path']}   ({i['channel']}, {i['version']})" for i in installs
            ]
            choice, ok = QInputDialog.getItem(
                self, "Select YARG install", "Multiple installs found:", labels, 0, False
            )
            if not ok:
                return
            chosen = installs[labels.index(choice)]
        self.yarg_picker.setText(chosen["path"])
        self.log_panel.log(
            f"Selected: {chosen['path']}   ({chosen['channel']}, {chosen['version']})"
        )

    def on_regenerate_sources(self):
        self._persist_settings()
        install_dir = self.yarg_picker.text()
        if not install_dir or not os.path.isfile(os.path.join(install_dir, "YARG.exe")):
            installs = find_yarg_installs()
            if len(installs) == 1:
                install_dir = installs[0]["path"]
            elif len(installs) > 1:
                labels = [
                    f"{i['path']}   ({i['channel']}, {i['version']})" for i in installs
                ]
                choice, ok = QInputDialog.getItem(
                    self, "Select YARG install", "Multiple installs found:", labels, 0, False
                )
                if not ok:
                    return
                install_dir = installs[labels.index(choice)]["path"]
            else:
                QMessageBox.warning(
                    self, "No install",
                    "No YARG install found. Set the install folder first "
                    "(or click Auto-detect).",
                )
                return

        if not install_dir or not os.path.isfile(os.path.join(install_dir, "YARG.exe")):
            QMessageBox.warning(
                self, "Invalid install",
                "The selected folder does not contain YARG.exe.",
            )
            return

        self.yarg_picker.setText(install_dir)
        self.log_panel.log(f"Regenerating sources from {install_dir} …")
        self._start_worker(regenerate_sources, self._on_regenerate_done, install_dir)

    def _on_regenerate_done(self, result):
        self.sources = result["sources"]
        self.log_panel.log(
            f"Wrote {result['path']} with {len(result['sources'])} source ids."
        )
        # Refresh the source list with the updated registry (and scan if available).
        if self.scan_cache:
            self._persist_settings()
            self.on_scan()
        else:
            self._refresh_sources()

    def on_open_output_folder(self):
        out_dir = self.output_picker.text()
        if not out_dir:
            out_dir = CAREERS_DIR if CAREERS_DIR.exists() else CAREERS_DIR.parent
        self._open_path(str(out_dir))

    def on_open_settings_json(self):
        os.startfile(str(SETTINGS_PATH))

    def _apply_structure(self, result, loaded_filename):
        self.settings["career"] = result["career"]
        self.settings["tiers"] = result["tiers"]
        self.settings["loaded_career"] = loaded_filename
        self.settings["setlist"] = {
            t["id"]: list(songs)
            for t, songs in zip(result["tiers"], result.get("songs", []))
        }
        self._load_settings_into_ui()
        self._persist_settings()
        self._refresh_setlist()
        self._setlist_dirty = False
        self.update_setlist_btn.setEnabled(False)
        self._career_dirty = False

    def on_load_career(self):
        if not self._confirm_discard_edits():
            return
        start = str(CAREERS_DIR) if CAREERS_DIR.exists() else str(BASE)
        path, _ = QFileDialog.getOpenFileName(
            self, "Load career", start, "Career files (*.json *.preset)"
        )
        if not path:
            return
        try:
            result = load_career_file(path)
        except Exception as exc:
            QMessageBox.critical(self, "Load failed", f"Could not load career:\n{exc}")
            return
        self._apply_structure(result, os.path.basename(path))
        self.log_panel.log(f"Loaded career: {os.path.basename(path)}")

    def on_import_template(self):
        if not self._confirm_discard_edits():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Import template (YARG export)", str(BASE), "YARG preset (*.preset *.json)"
        )
        if not path:
            return
        try:
            import_template(path)
            result = load_template()
        except Exception as exc:
            QMessageBox.critical(self, "Import failed", f"Could not import template:\n{exc}")
            return
        self._apply_structure(result, None)
        self.log_panel.log(f"Imported template: {os.path.basename(path)}")

    def on_reset_to_template(self):
        if not self._confirm_discard_edits():
            return
        try:
            result = load_template()
        except Exception as exc:
            QMessageBox.critical(self, "Reset failed", f"Could not load template:\n{exc}")
            return
        self._apply_structure(result, None)
        self.log_panel.log("Reset to default template.")

    def on_reset_to_default(self):
        if not self._confirm_discard_edits():
            return
        try:
            import_template(str(BUNDLED_TEMPLATE_PATH))
            result = load_template()
        except Exception as exc:
            QMessageBox.critical(self, "Reset failed", f"Could not reset to default:\n{exc}")
            return
        self._apply_structure(result, None)
        self.log_panel.log("Reset to shipped default career.")

    def on_save_setlist(self):
        self._persist_settings()
        career = self.settings.get("career", {}) or {}
        out_dir = self.settings.get("output_dir") or CAREERS_DIR
        name = sanitize_filename(career.get("name") or "Career")
        json_path = os.path.join(str(out_dir), f"{name}.json")
        preset_path = os.path.join(str(out_dir), f"{name}.preset")

        if os.path.exists(json_path) or os.path.exists(preset_path):
            reply = QMessageBox.question(
                self, "Overwrite career?",
                f"This will overwrite:\n  {json_path}\n  {preset_path}\n\nContinue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        setlist = self.settings.get("setlist") or {}
        result = save_setlist(self.settings, self.sources, setlist)
        self.settings["loaded_career"] = os.path.basename(result["json_path"])
        save_settings(self.settings)
        self.log_panel.log(f"Saved setlist:\n  {result['json_path']}\n  {result['preset_path']}")
        self.statusBar().showMessage("Setlist saved")
        self._refresh_careers()

    def on_toggle_theme(self):
        from .theme import apply_theme
        self._dark = not self._dark
        apply_theme(QApplication.instance(), dark=self._dark)

    def on_about(self):
        AboutDialog(self).exec()

    def _open_path(self, path):
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Not found", f"Folder does not exist:\n{path}")
            return
        os.startfile(path)
