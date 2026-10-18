"""Source registry + YARG install detection."""

import json
import os
import string

from ..paths import SOURCES_PATH


def source_info(sources, source_id):
    return sources.get(source_id, None)


def is_public_allowed(source_id, sources, allowed_types, always_allowed_ids):
    if source_id in always_allowed_ids:
        return True
    info = source_info(sources, source_id)
    if info is None:
        return False
    return info.get("type") in allowed_types


# --------------------------------------------------------------------------- #
#  YARG install detection
# --------------------------------------------------------------------------- #

def _drive_letters():
    # C: first, then the rest alphabetically
    letters = sorted(string.ascii_uppercase, key=lambda c: (0 if c == "C" else 1, c))
    return [f"{c}:\\" for c in letters]


def _read_tag_version(install_dir):
    # tag.txt lives next to the `installation` folder (one level up)
    tag = os.path.join(os.path.dirname(install_dir), "tag.txt")
    try:
        with open(tag, "r", encoding="utf-8-sig") as f:
            return f.read().strip() or "?"
    except OSError:
        return "?"


def _load_launcher_channels():
    """Map install UUID -> launcher releaseName (e.g. 'Nightly'/'Stable'). {} if unavailable."""
    channels = {}
    try:
        appdata = os.environ.get("APPDATA") or ""
        path = os.path.join(appdata, "in.yarg.launcher", "settings.json")
        if not os.path.isfile(path):
            return channels
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        for prof in data.get("activeProfiles", []):
            release_name = prof.get("profile", {}).get("metadata", {}).get("releaseName")
            if prof.get("uuid") and release_name:
                channels[prof["uuid"]] = release_name
    except Exception:
        pass
    return channels


def _resolve_channel(install_id, version, channels=None):
    """Label an install as Nightly/Stable. Prefers the launcher releaseName, then the tag."""
    if channels is None:
        channels = _load_launcher_channels()
    if install_id and install_id in channels:
        return channels[install_id]
    if version and version != "?":
        return "Stable" if version.lower().startswith("v") else "Nightly"
    return "?"


def find_yarg_installs():
    """Find YARG installs across all drives (C: first). Returns list of {path, version, channel}."""
    installs = []
    seen = set()
    channels = _load_launcher_channels()

    def add(path, install_id=None):
        path = os.path.normpath(path)
        if path in seen:
            return
        if not os.path.isfile(os.path.join(path, "YARG.exe")):
            return
        seen.add(path)
        version = _read_tag_version(path)
        installs.append({
            "path": path,
            "version": version,
            "channel": _resolve_channel(install_id, version, channels),
        })

    for drive in _drive_letters():
        if not os.path.exists(drive):
            continue
        # YARC launcher layout: X:\YARC\YARG Installs\<id>\installation
        base = os.path.join(drive, "YARC", "YARG Installs")
        if os.path.isdir(base):
            try:
                for entry in os.listdir(base):
                    add(os.path.join(base, entry, "installation"), install_id=entry)
            except OSError:
                pass
        # common portable/standalone locations
        for rel in ("YARG", "Program Files\\YARG", "Program Files (x86)\\YARG"):
            add(os.path.join(drive, rel))

    return installs


def build_sources_from_install(install_dir):
    """Read base + extra OpenSource index.json and flatten to {id: {name, type, group}}."""
    sources = {}
    registry = os.path.join(install_dir, "YARG_Data", "StreamingAssets", "sources", "OpenSource-master")
    if not os.path.isdir(registry):
        raise FileNotFoundError(f"OpenSource registry not found under: {registry}")

    for group in ("base", "extra"):
        p = os.path.join(registry, group, "index.json")
        if not os.path.isfile(p):
            continue
        with open(p, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        for entry in data.get("sources", []):
            names = entry.get("names", {})
            name = names.get("en-US") or next(iter(names.values()), "")
            typ = entry.get("type", "")
            keys = list(entry.get("ids", [])) + ([entry["icon"]] if entry.get("icon") else [])
            for k in keys:
                if k and k != "$DEFAULT$":
                    sources.setdefault(k, {"name": name, "type": typ, "group": group})
    return sources


def write_sources_file(sources, path=SOURCES_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"sources": sources}, f, indent=2, sort_keys=True, ensure_ascii=False)
    return path


def merged_source_rows(sources, counts, allowed_types, always_allowed_ids):
    """Union the source registry (from a YARG install) with library scan counts.

    Returns a list of rows {source, name, type, count, public}. Sources present
    in the library come first (highest count first); registry-only sources
    follow with a count of 0 (sorted by name).
    """
    rows = []
    seen = set()

    for src_id, count in counts.items():
        info = sources.get(src_id)
        rows.append({
            "source": src_id,
            "name": info["name"] if info else "?",
            "type": info["type"] if info else "?",
            "count": count,
            "public": is_public_allowed(src_id, sources, allowed_types, always_allowed_ids),
        })
        seen.add(src_id)

    for src_id, info in sources.items():
        if src_id in seen:
            continue
        rows.append({
            "source": src_id,
            "name": info["name"],
            "type": info["type"],
            "count": 0,
            "public": is_public_allowed(src_id, sources, allowed_types, always_allowed_ids),
        })

    rows.sort(key=lambda r: (0 if r["count"] > 0 else 1, -r["count"], r["name"].lower()))
    return rows
