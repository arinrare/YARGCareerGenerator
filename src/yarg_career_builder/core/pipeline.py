"""End-to-end build orchestration shared by the CLI and GUI.

Pure (GUI-free) functions that glue the lower-level modules together and return
structured results / raise typed errors, so callers can render them however they
like (terminal text, a Qt view, logs, etc.).
"""

from collections import Counter

from .config import load_settings, load_sources
from .scan import scan_library
from .selection import select_and_sort_songs, apply_source_selection
from .sources import source_info, is_public_allowed
from .tiering import redistribute
from .generate import make_tier_json, make_preset_json, write_outputs


class PublicBlockError(Exception):
    """Raised when a public career would include a forbidden source."""

    def __init__(self, violations):
        self.violations = violations
        super().__init__("public career blocked")


class NoSongsError(Exception):
    """Raised when nothing is selected for the career."""


def scan_report(settings, sources):
    """Scan the library and return counts + per-source rows for display."""
    music_root = settings.get("music_root")
    songs = scan_library(music_root)

    counts = Counter(s["source"] for s in songs if s["source"])
    no_source = sum(1 for s in songs if not s["source"])

    tiers_cfg = settings.get("tiers", [])
    target = sum(int(t.get("song_count", 0)) for t in tiers_cfg)

    pc = settings.get("public_checks", {})
    allowed_types = pc.get("allowed_types", [])
    always_allowed = pc.get("always_allowed_ids", [])

    rows = []
    for src, count in counts.most_common():
        info = source_info(sources, src)
        rows.append({
            "source": src,
            "name": info["name"] if info else "?",
            "type": info["type"] if info else "?",
            "count": count,
            "public": is_public_allowed(src, sources, allowed_types, always_allowed),
        })

    return {
        "songs": songs,
        "music_root": music_root,
        "counts": dict(counts),
        "no_source": no_source,
        "target": target,
        "tier_count": len(tiers_cfg),
        "rows": rows,
    }


def build_career(settings, sources):
    """Run the full build pipeline and return a result dict.

    Raises FileNotFoundError (bad music_root), ValueError (no tiers),
    PublicBlockError, or NoSongsError.
    """
    music_root = settings.get("music_root")
    songs = scan_library(music_root)

    usable, excluded = select_and_sort_songs(songs, settings, sources)

    tiers_cfg = settings.get("tiers", [])
    if not tiers_cfg:
        raise ValueError("settings.json has no 'tiers'.")
    target = sum(int(t.get("song_count", 0)) for t in tiers_cfg)

    selected, breakdown = apply_source_selection(usable, settings, target)

    # ---- public hard-block -------------------------------------------------
    visibility = settings.get("visibility", "private")
    violations = {}
    if visibility == "public":
        pc = settings.get("public_checks", {})
        allowed_types = set(pc.get("allowed_types", []))
        always_allowed = set(pc.get("always_allowed_ids", []))
        for s in selected:
            if not is_public_allowed(s["source"], sources, allowed_types, always_allowed):
                violations.setdefault(s["source"], []).append(s["title"])
    if violations:
        raise PublicBlockError(violations)

    if not selected:
        raise NoSongsError()

    # ---- tier filling ------------------------------------------------------
    weights = [int(t.get("song_count", 0)) for t in tiers_cfg]
    counts = redistribute(weights, len(selected))

    filled = []
    cursor = 0
    for tier_cfg, n in zip(tiers_cfg, counts):
        chunk = selected[cursor:cursor + n]
        cursor += n
        filled.append((tier_cfg, chunk))

    # ---- emit --------------------------------------------------------------
    tiers_json = [make_tier_json(cfg, chunk) for cfg, chunk in filled]
    preset = make_preset_json(settings.get("career", {}), tiers_json)
    json_path, preset_path = write_outputs(preset, settings.get("career", {}), settings)

    return {
        "songs_scanned": len(songs),
        "excluded": excluded,
        "selected": selected,
        "breakdown": breakdown,
        "filled": filled,
        "json_path": json_path,
        "preset_path": preset_path,
        "career": settings.get("career", {}),
        "visibility": visibility,
    }


def load_defaults():
    """Load settings + sources (used by both CLI and GUI entry points)."""
    return load_settings(), load_sources()


def regenerate_sources(install_dir):
    """Rebuild sources.json from a YARG install's OpenSource registry."""
    from .sources import build_sources_from_install, write_sources_file
    new_sources = build_sources_from_install(install_dir)
    path = write_sources_file(new_sources)
    return {"sources": new_sources, "path": path}
