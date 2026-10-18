"""Portable path resolution.

The app is designed to be fully portable: settings.json, sources.json and
generated careers all live in the application's base directory, never in the
user's home/appdata folders.

Base directory resolution:
- Frozen (PyInstaller one-folder): the folder that contains the executable.
- Source checkout (development): the repository root (two levels above this
  file, i.e. the folder that contains ``src/`` and ``settings.json``).

Built careers are always written into the distributable folder's ``careers``
subfolder (``dist/YARG Career Builder/careers``), so the whole distributable can
be zipped and shared as one self-contained unit.
"""

import sys
from pathlib import Path

# Must match the COLLECT/EXE ``name`` in packaging/yarg_career_builder.spec.
APP_DIR_NAME = "YARG Career Builder"


def is_frozen() -> bool:
    """True when running from a PyInstaller-built executable."""
    return bool(getattr(sys, "frozen", False))


def base_dir() -> Path:
    """Return the application base directory (where config data files live)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    # dev: this file lives at <root>/src/yarg_career_builder/paths.py
    return Path(__file__).resolve().parents[2]


def dist_dir() -> Path:
    """Return the distributable folder (where the built executable lives)."""
    if is_frozen():
        return base_dir()
    return base_dir() / "dist" / APP_DIR_NAME


def bundled_dir() -> Path:
    """Return the directory that holds bundled read-only resources."""
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        return Path(meipass) if meipass else base_dir()
    return base_dir()


BASE = base_dir()
BUNDLED = bundled_dir()
SETTINGS_PATH = BASE / "settings.json"
SOURCES_PATH = BASE / "sources.json"
CAREERS_DIR = dist_dir() / "careers"

# The default career template: a user-replaceable YARG .preset export.
# TEMPLATE_PATH is the live file (next to settings.json); BUNDLED_TEMPLATE_PATH
# is the shipped pristine copy used to seed TEMPLATE_PATH on first run.
TEMPLATE_PATH = BASE / "Template.preset"
BUNDLED_TEMPLATE_PATH = BUNDLED / "templates" / "Template.preset"
