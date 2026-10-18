# YARG Career Builder

A dark-themed desktop GUI (with an optional CLI) that builds **YARG career presets**
from the song folders in your library — no in-game editor needed. Songs are referenced
by **Song Tuple** (title, artist, charter, source), so the resulting career is portable
and shareable.

## Features

- **Dark theme** desktop app (Qt / PySide6) with a classic Windows menu bar
  (**File / View / Settings / Help**).
- **Folder pickers** for the YARG install, music library, and output directory,
  plus **auto-detect** for YARG installs (scans all drives, C: first, and labels
  each install **Nightly** or **Stable**).
- **Buttons** for the launch options: **Scan Library**, **Regenerate Sources**, **Build Career**.
- **Career tab** — name/title/description/source/version/type, visibility
  (private/public), difficulty field, sort order, and missing-difficulty handling.
- **Sources tab** — a filterable source table (text search, type filter, public-only)
  with include checkboxes, and a **filter/limit** or **weighted** selection mode.
- **Tiers tab** — read-only view of the career tier structure (a visual tier editor
  is planned).
- Live **"selected / target"** readout and an output log panel.
- Export both `<name>.json` (import via YARG → Presets → Career → Import) and
  `<name>.preset` (the zipped export form).
- **Fully portable** — no user-folder access; all data lives in the app folder.

---

## Quick start (prebuilt app)

1. Download or build the distributable folder `YARG Career Builder/`.
2. Double-click `YARG Career Builder.exe`.
3. On first run the app creates `settings.json` and `sources.json` next to the
   executable. Point the app at your **YARG install** and **music library**, then:
   - **Regenerate Sources** — rebuild the source registry from your YARG install.
   - **Scan Library** — list songs per source and pick which sources to use.
   - **Build Career** — generate the career files.

---

## Developer setup (fresh checkout → built app)

Prerequisites: **Python 3.12+** (3.14 tested) and **git**.

### One-click (double-click the batch file)

| File | What it does |
|---|---|
| `install.bat` | Create `.venv` (if missing) and install all dependencies from `requirements.txt`. Run once, or whenever deps change. |
| `build.bat`  | Build the distributable (`dist\YARG Career Builder\`). Auto-runs `install.bat` first if the environment is missing. |
| `run.bat`    | Launch the GUI (no console window). Auto-runs `install.bat` first if the environment is missing. |
| `test.bat`   | Run the test suite. Auto-runs `install.bat` first if the environment is missing. |

A fresh checkout is just double-click `build.bat` (or `run.bat` / `test.bat`) —
they self-install on first run and skip the install afterwards. Re-run
`install.bat` manually when you update `requirements.txt`.

### Or, via the command line

All dependencies (runtime + build + test) are pinned in a single `requirements.txt`.
A fresh checkout can be built with **one command**:

```powershell
.\scripts\build.ps1
```

That script does the entire pipeline: create a virtual environment,
`pip install -r requirements.txt`, and run PyInstaller to produce a portable
one-folder distribution. The result is written to:

```
dist\YARG Career Builder\YARG Career Builder.exe
```

### Or, do it step-by-step

```powershell
git clone <repo-url>
cd "YARG Careers"

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

pyinstaller packaging\yarg_career_builder.spec --noconfirm
```

---

## Run from source (development)

Double-click **`run.bat`**, or run:

```powershell
.\scripts\run.ps1        # launches the GUI (with console, for debugging)
```

Or manually:

```powershell
.venv\Scripts\activate
set PYTHONPATH=src
python -m yarg_career_builder              # GUI
python -m yarg_career_builder.cli scan     # CLI: list songs + per-source counts
python -m yarg_career_builder.cli build    # CLI: generate the career
python -m yarg_career_builder.cli regenerate-sources
```

---

## Configuration (`settings.json`)

`settings.json` holds all configuration. Key sections:

| Key | Meaning |
|---|---|
| `music_root` | Folder scanned for song folders (each containing a `song.ini`). |
| `output_dir` | Where built careers are written. Leave `""` to write into `dist\YARG Career Builder\careers` (the distributable folder). |
| `yarg.install_dir` | YARG install folder (contains `YARG.exe`). Leave `""` to auto-detect. |
| `visibility` | `"private"` (any source) or `"public"` (hard-block unless every source is a general custom/charter or YARC content). |
| `difficulty.field` | `song.ini` key used to sort (e.g. `diff_guitar`, `diff_band`, `diff_drums`, `diff_vocals`). |
| `difficulty.missing` | `"last"` keeps songs with no difficulty at the end; `"skip"` drops them. |
| `source_selection.filter` | Source ids to use (empty = all). |
| `source_selection.limit` | Cap on the number of distinct sources (0 = unlimited). |
| `source_selection.weights` | Optional map `source id -> weight`; if non-empty it overrides `filter`/`limit`. |
| `loaded_career` | Filename of the last loaded/built career (restored on startup if it still exists). |

A documented default lives in `config/settings.default.json` (copied to
`settings.json` on first run if missing).

## Career structure & template

The **career structure** (the list of tiers — names, song counts, unlock
criteria, bonus flags, venue hints, unlock text) plus the career **metadata**
(name, title, description) are derived from a **template**: a YARG `.preset`
export stored at `Template.preset` (next to `settings.json`).

- **First run** seeds `Template.preset` from the bundled default
  (`templates/Template.preset`) and builds the initial structure from it.
- **Edit the structure** in the **Tiers** tab (add/remove/reorder tiers, edit
  their fields).
- **File → Import Template…** supplies a *new* default template from a YARG
  export (replaces `Template.preset` and loads it).
- **File → Load Career…** loads an existing career from the `careers` folder
  (structure + metadata only; source selection is unchanged).
- **File → Reset to Template** restores the current template.
- **On startup**, the app reloads the last loaded/built career if its file still
  exists in the `careers` folder; otherwise it loads the template.

## How songs are referenced

Each song is written as a **Song Tuple**:

```json
{
  "SongTuple": { "Artist": "Blink-182", "Title": "Dammit (Growing Up)", "Source": "ghwt", "Charter": "Neversoft" },
  "Identifier": "SongTuple"
}
```

The four values come from each song folder's `song.ini`:

| Tuple field | `song.ini` key |
|---|---|
| Title | `name` |
| Artist | `artist` |
| Charter | `charter` (fallback `frets`) |
| Source | `icon` |

## `sources.json`

Generated from a YARG install's `StreamingAssets\sources\OpenSource-master`
registry (base + extra `index.json`). Rebuild it any time with **Regenerate
Sources** (GUI) or `regenerate-sources` (CLI). The release/retail build ships
only `base`; the nightly build also ships `extra` (community/custom sources).

## Portability

The app is fully portable: `settings.json`, `sources.json`, and built careers all
live in the application folder (next to the executable), never in
`%APPDATA%` or the user's home directory. Built careers are written to
`dist\YARG Career Builder\careers\` by default (in both the GUI and the CLI), so
zipping the whole `YARG Career Builder\` folder captures everything: the
executable, config, and output.

## Testing

Double-click **`test.bat`**, or run:

```powershell
.venv\Scripts\python.exe -m pytest
```

## Project layout

```
src/yarg_career_builder/
├── app.py             # Qt bootstrap
├── cli.py             # command-line interface
├── paths.py           # portable base-dir resolution
├── core/              # GUI-free logic (scan, selection, tiering, generate, config, sources, pipeline, career_io, bootstrap)
└── ui/                # Qt UI (main window, theme, widgets incl. tier_editor, dialogs, workers)
assets/                # app icon (CC0 guitar) + attribution
config/                # shipped defaults (seeded on first run)
templates/             # default career template (Template.preset)
packaging/             # PyInstaller spec + entry point
scripts/               # build.ps1 / run.ps1 / make_icon.py
tests/                 # pytest suite
install.bat            # one-click dependency install (double-click)
build.bat              # one-click build (double-click)
run.bat                # one-click run (double-click)
test.bat               # one-click tests (double-click)
```

### Icon

The app icon is a public-domain (CC0) guitar illustration; see
`assets/ATTRIBUTION.md`. Regenerate it any time with
`.\scripts\make_icon.py`. The YARG logo is a YARC trademark and is intentionally
not used.

