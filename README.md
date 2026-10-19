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
- **Tiers tab** — a full tier editor: add/remove/reorder tiers and edit every
  YARG tier option (name, description, unlock type/criteria, bonus flag, venue
  size/hint, completion mode, custom unlock text, completion bonus, and
  completion-bonus media).
- **Careers tab** — list the careers in the output folder, load one into the
  editor, delete a career (its `.json`, `.preset`, and — when no longer used —
  its media), and remove media left behind by careers that no longer exist.
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

## Creating a release (GitHub Actions)

Pushing a version tag triggers a workflow (`.github/workflows/release.yml`) that
builds the app and attaches a `YargCareerBuilder.zip` to a new GitHub release.

1. (Optional) bump the version in `src/yarg_career_builder/_version.py`.
2. Commit, tag, and push:

```powershell
git add -A
git commit -m "Release v1.2.3"
git tag v1.2.3
git push origin main v1.2.3
```

The workflow then:

- builds the one-folder app with PyInstaller,
- injects the tag version into the build (so the About dialog shows `1.2.3`),
- zips `dist\YARG Career Builder\` into `YargCareerBuilder.zip`,
- creates a GitHub release named `v1.2.3` with the zip attached.

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

## Tier options

Each tier in the **Tiers** tab exposes the full set of options YARG supports for a
career tier, matching the fields written to the preset file:

| Option | Values | Meaning |
|---|---|---|
| Name | Text | The tier's display name shown in the career menu. |
| Description | Text | Optional tier-level flavour text (stored in the preset's `Description`). |
| Song count | Number (≥ 1) | Relative number of songs; used to split the selected songs across tiers. |
| Unlock type | `StarCount` / `CompletionCount` | `StarCount` unlocks on the running star total; `CompletionCount` unlocks on the number of completed songs. |
| Unlock criteria | Number (≥ 0) | Stars (StarCount) or completed songs (CompletionCount) required to unlock this tier. |
| Bonus tier | Yes / No | Optional side-setlist. Bonus tiers don't count toward unlocking later tiers. |
| Venue size | `NotSpecified` / `Starter` / `Small` / `Medium` / `Large` / `Epic` | Approximate stage size used for venue selection. |
| Venue hint | Text | Optional venue path (e.g. `Venue/Church`), or type a custom `Venue/<name>`. |
| Completion mode | `SingleSong` / `FullTierPlaylist` / `FullCareerPlaylist` | How the tier's songs are completed. Playlist modes are stored but not yet honored by YARG gameplay. |
| Custom unlock text | Text | Flavour text shown when the tier unlocks. |
| Completion bonus | `None` / `Image` / `Sound` / `Video` | What to show when the tier is completed. |
| Completion bonus text | Text | Text shown when the completion bonus triggers. |
| Media file | File picker (`png`/`jpg`/`jpeg` images, `webm` video, `ogg`/`mp3`/`wav`/`flac` audio) | The media shown/played on completion. Copied into the app's `media` folder and embedded in the exported `.preset`. |
| Clear media file | Button | Removes the tier's completion-bonus media file. |

Media is stored in the `.preset` archive as a separate entry keyed by filename
(the JSON only records the filename in `MediaFilename`), so exported careers stay
self-contained. The app keeps its own working copy of each career's media in a
per-career folder `media/<career-id>/` (keyed by the career's stable `Id`, which
is preserved across builds so a shared preset round-trips unchanged). Loading or
importing a `.preset` extracts its media back into that folder; loading a plain
`.json` has no media (it was never embedded). Unreferenced media files are
removed automatically, and the **Careers** tab can delete whole careers or clean
up media left behind by careers that no longer exist.