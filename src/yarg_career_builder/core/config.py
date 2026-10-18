"""Configuration loading (settings.json / sources.json).

On first run (or if a data file is missing) the shipped defaults from the
``config/`` directory are copied into the base directory, so a fresh
distributable is immediately usable.
"""

import json
import shutil

from ..paths import BASE, BUNDLED, SETTINGS_PATH, SOURCES_PATH

DEFAULT_SETTINGS_NAME = "settings.default.json"
DEFAULT_SOURCES_NAME = "sources.default.json"


def _default_candidates(name):
    return [BASE / "config" / name, BUNDLED / "config" / name]


def _ensure_file(target, default_name):
    if target.exists():
        return
    for candidate in _default_candidates(default_name):
        if candidate.exists():
            shutil.copyfile(candidate, target)
            return


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_settings():
    _ensure_file(SETTINGS_PATH, DEFAULT_SETTINGS_NAME)
    return load_json(SETTINGS_PATH)


def load_sources():
    _ensure_file(SOURCES_PATH, DEFAULT_SOURCES_NAME)
    return load_json(SOURCES_PATH).get("sources", {})


def save_settings(settings):
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    return SETTINGS_PATH
