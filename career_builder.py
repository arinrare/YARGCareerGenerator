#!/usr/bin/env python3
"""
YARG Career Builder
-------------------
Builds a YARG "Career" preset (as a portable Song-Tuple career) from the song
folders in your library, so you don't have to add/remove songs one-by-one in
the in-game editor.

Usage:
    python career_builder.py scan       # list songs + per-source counts
    python career_builder.py build      # generate the career (.json + .preset)

Configuration lives in settings.json (next to this script).
A song source registry (icon id -> name/type) lives in sources.json.

The whole thing is stdlib-only (no pip installs required).
"""

import argparse
import configparser
import hashlib
import io
import json
import os
import sys
import uuid
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(BASE, "settings.json")
SOURCES_PATH = os.path.join(BASE, "sources.json")

# song.ini keys used to build a Song Tuple
KEY_NAME = "name"
KEY_ARTIST = "artist"
KEY_CHARTER = "charter"
KEY_CHARTER_FALLBACK = "frets"
KEY_SOURCE = "icon"


# --------------------------------------------------------------------------- #
#  Loading / parsing helpers
# --------------------------------------------------------------------------- #

def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_settings():
    return load_json(SETTINGS_PATH)


def load_sources():
    return load_json(SOURCES_PATH).get("sources", {})


def parse_ini(path):
    """Read a song.ini into a dict of key -> value (lowercased keys)."""
    result = {}
    section = ""
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith((";", "#")):
                continue
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].lower()
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip().lower()
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                result[key] = value
    return result


def scan_library(music_root):
    """Return a list of song dicts found under music_root."""
    songs = []
    if not music_root or not os.path.isdir(music_root):
        print(f"ERROR: music_root does not exist: {music_root}")
        sys.exit(1)

    for dirpath, dirnames, filenames in os.walk(music_root):
        if "song.ini" not in filenames:
            continue
        ini = parse_ini(os.path.join(dirpath, "song.ini"))
        title = (ini.get(KEY_NAME) or "").strip()
        artist = (ini.get(KEY_ARTIST) or "").strip()
        charter = (ini.get(KEY_CHARTER) or ini.get(KEY_CHARTER_FALLBACK) or "").strip()
        source = (ini.get(KEY_SOURCE) or "").strip()
        songs.append({
            "folder": dirpath,
            "title": title,
            "artist": artist,
            "charter": charter,
            "source": source,
            "ini": ini,
        })
    return songs


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
#  Song selection / difficulty
# --------------------------------------------------------------------------- #

def difficulty_value(song, settings):
    field = settings["difficulty"].get("field", "diff_guitar")
    raw = song["ini"].get(field.lower())
    try:
        return int(raw)
    except (TypeError, ValueError):
        return -1


def difficulty_sort_key(song, ascending):
    # missing difficulty (-1) sorts last when ascending
    d = song["difficulty"]
    if ascending:
        return (0 if d >= 0 else 1, d if d >= 0 else 0, song["title"].lower())
    return (0 if d >= 0 else 1, -(d if d >= 0 else 0), song["title"].lower())


def select_and_sort_songs(songs, settings, sources):
    """Sanity-check + difficulty sort. Returns (usable, excluded)."""
    dif_settings = settings["difficulty"]
    ascending = dif_settings.get("ascending", True)
    missing = dif_settings.get("missing", "last")

    usable = []
    excluded = {"missing_meta": [], "no_guitar": []}

    for s in songs:
        if not (s["title"] and s["artist"] and s["charter"] and s["source"]):
            excluded["missing_meta"].append(s)
            continue
        s["difficulty"] = difficulty_value(s, settings)
        usable.append(s)

    if missing == "skip":
        kept = []
        for s in usable:
            if s["difficulty"] < 0:
                excluded["no_guitar"].append(s)
            else:
                kept.append(s)
        usable = kept

    usable.sort(key=lambda s: difficulty_sort_key(s, ascending))
    return usable, excluded


def allocate_sources(weights, target, available):
    """Split `target` songs across sources in proportion to `weights`, clamped to `available`."""
    weights = {k: float(w) for k, w in weights.items() if w and float(w) > 0}
    if not weights or target <= 0:
        return {}

    total_w = sum(weights.values())
    quotas = {src: target * w / total_w for src, w in weights.items()}
    takes = {src: int(q) for src, q in quotas.items()}
    rem = target - sum(takes.values())
    order = sorted(weights, key=lambda s: quotas[s] - takes[s], reverse=True)
    idx = 0
    while rem > 0:
        takes[order[idx % len(order)]] += 1
        rem -= 1
        idx += 1

    # clamp to what each source actually has, then give any shortfall to sources with spare capacity
    shortfall = 0
    for src in takes:
        avail = available.get(src, 0)
        if takes[src] > avail:
            shortfall += takes[src] - avail
            takes[src] = avail
    if shortfall > 0:
        by_weight = sorted(weights, key=lambda s: -weights[s])
        idx = 0
        while shortfall > 0:
            src = by_weight[idx % len(by_weight)]
            spare = available.get(src, 0) - takes[src]
            if spare > 0:
                add = min(shortfall, spare)
                takes[src] += add
                shortfall -= add
            idx += 1
            if idx > len(by_weight) * 10000:
                break

    return {src: n for src, n in takes.items() if n > 0}


def apply_source_selection(usable, settings, target):
    """Decide which sources contribute and how many songs each contributes.
    `usable` must already be difficulty-sorted. Returns (selected, breakdown)."""
    from collections import Counter, defaultdict

    sel = settings.get("source_selection", {})
    weights = sel.get("weights") or {}
    source_filter = [s.lower() for s in (sel.get("filter") or [])]
    source_limit = int(sel.get("limit") or 0)
    ascending = settings["difficulty"].get("ascending", True)

    by_source = defaultdict(list)
    for s in usable:
        by_source[s["source"]].append(s)

    if weights:
        weights = {k.lower(): w for k, w in weights.items() if w}
        available = {src: len(lst) for src, lst in by_source.items()}
        takes = allocate_sources(weights, target, available)
        selected = []
        for src, lst in by_source.items():
            n = takes.get(src, 0)
            if n > 0:
                selected.extend(lst[:n])  # each source's easiest songs first
        breakdown = dict(takes)
    else:
        selected = usable
        if source_filter:
            selected = [s for s in selected if s["source"].lower() in source_filter]
        if source_limit > 0:
            top = {src for src, _ in Counter(s["source"] for s in selected).most_common(source_limit)}
            selected = [s for s in selected if s["source"] in top]
        breakdown = dict(Counter(s["source"] for s in selected))

    selected.sort(key=lambda s: difficulty_sort_key(s, ascending))
    return selected, breakdown


# --------------------------------------------------------------------------- #
#  Tier distribution
# --------------------------------------------------------------------------- #

def redistribute(weights, total):
    """Split `total` items across buckets whose relative sizes are `weights`."""
    weights = [max(int(w), 0) for w in weights]
    s = sum(weights)
    if total <= 0 or s <= 0:
        return [0] * len(weights)

    if total == s:
        return list(weights)

    scaled = [w * total / s for w in weights]
    floors = [int(x) for x in scaled]
    rem = total - sum(floors)
    order = sorted(range(len(weights)), key=lambda i: scaled[i] - floors[i], reverse=True)
    idx = 0
    while rem > 0:
        floors[order[idx % len(order)]] += 1
        rem -= 1
        idx += 1
    return floors


# --------------------------------------------------------------------------- #
#  Output generation
# --------------------------------------------------------------------------- #

def tuple_id(artist, title, source, charter):
    # Matches YARG's own convention: Guid(MD5("Artist - Title - Source - Charter"))
    raw = f"{artist} - {title} - {source} - {charter}"
    return str(uuid.UUID(bytes=hashlib.md5(raw.encode("utf-8")).digest()))


def make_song_json(song):
    artist, title, source, charter = song["artist"], song["title"], song["source"], song["charter"]
    return {
        "Id": tuple_id(artist, title, source, charter),
        "SongId": None,
        "SongHash": None,
        "ShortName": None,
        "SongTuple": {
            "Artist": artist,
            "Title": title,
            "Source": source,
            "Charter": charter,
        },
        "Identifier": "SongTuple",
        "Description": None,
    }


def make_tier_json(tier_cfg, songs):
    return {
        "Name": tier_cfg["name"],
        "Id": str(uuid.uuid4()),
        "Description": None,
        "Songs": [make_song_json(s) for s in songs],
        "CustomUnlockText": tier_cfg.get("custom_unlock_text"),
        "BackgroundImage": None,
        "CompletionBonusText": None,
        "CompletionBonus": "None",
        "MediaFilename": None,
        "VenueSize": "NotSpecified",
        "VenueHint": tier_cfg.get("venue_hint"),
        "UnlockType": "StarCount",
        "UnlockCriteria": int(tier_cfg.get("unlock_criteria", 0)),
        "CompletionMode": "SingleSong",
        "IsBonus": bool(tier_cfg.get("is_bonus", False)),
    }


def make_preset_json(career, tiers):
    return {
        "Title": career.get("title"),
        "Description": career.get("description"),
        "BackgroundImageName": None,
        "Source": career.get("source", "yarg"),
        "Version": int(career.get("version", 1)),
        "Name": career.get("name"),
        "Id": str(uuid.uuid4()),
        "Type": career.get("type", "Career"),
        "Tiers": tiers,
    }


def sanitize_filename(name):
    keep = []
    for ch in name:
        if ch.isalnum() or ch in "-_ ":
            keep.append(ch)
    return "".join(keep).strip().replace(" ", "_")


def write_outputs(preset, career, settings):
    out_dir = settings.get("output_dir") or BASE
    os.makedirs(out_dir, exist_ok=True)
    name = career.get("name") or "Career"
    sanitized = sanitize_filename(name)

    json_text = json.dumps(preset, indent=2, ensure_ascii=False)

    json_path = os.path.join(out_dir, f"{sanitized}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(json_text)

    preset_path = os.path.join(out_dir, f"{sanitized}.preset")
    with zipfile.ZipFile(preset_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("preset.json", json_text)

    return json_path, preset_path


# --------------------------------------------------------------------------- #
#  Commands
# --------------------------------------------------------------------------- #

def cmd_scan(settings, sources):
    music_root = settings.get("music_root")
    songs = scan_library(music_root)

    from collections import Counter, OrderedDict
    counts = Counter(s["source"] for s in songs if s["source"])
    no_source = sum(1 for s in songs if not s["source"])

    tiers_cfg = settings.get("tiers", [])
    target = sum(int(t.get("song_count", 0)) for t in tiers_cfg)

    print(f"Found {len(songs)} song folders under {music_root}")
    print(f"Career target: {target} songs across {len(tiers_cfg)} tiers "
          f"(set source_selection.filter to sources whose combined count is near {target})\n")
    if no_source:
        print(f"  ({no_source} songs have no 'icon' in song.ini and cannot be tuple-referenced)\n")

    rows = []
    for src, count in counts.most_common():
        info = source_info(sources, src)
        name = info["name"] if info else "?"
        typ = info["type"] if info else "?"
        allowed = is_public_allowed(
            src, sources,
            settings.get("public_checks", {}).get("allowed_types", []),
            settings.get("public_checks", {}).get("always_allowed_ids", []),
        )
        rows.append((src, name, typ, count, allowed))

    print(f"{'source':<16} {'type':<9} {'songs':>6}  {'public':<7} name")
    print("-" * 78)
    for src, name, typ, count, allowed in rows:
        print(f"{src:<16} {typ:<9} {count:>6}  {'yes' if allowed else 'no':<7} {name}")


def cmd_build(settings, sources):
    music_root = settings.get("music_root")
    songs = scan_library(music_root)
    print(f"Scanned {len(songs)} song folders.")

    usable, excluded = select_and_sort_songs(songs, settings, sources)

    if excluded["missing_meta"]:
        print(f"  - excluded {len(excluded['missing_meta'])} songs missing name/artist/charter/icon (cannot form a tuple).")
    if excluded["no_guitar"]:
        print(f"  - skipped {len(excluded['no_guitar'])} songs with no {settings['difficulty'].get('field')} part.")

    tiers_cfg = settings.get("tiers", [])
    if not tiers_cfg:
        print("ERROR: settings.json has no 'tiers'.")
        sys.exit(1)
    target = sum(int(t.get("song_count", 0)) for t in tiers_cfg)

    selected, breakdown = apply_source_selection(usable, settings, target)

    # ---- public hard-block -------------------------------------------------
    visibility = settings.get("visibility", "private")
    if visibility == "public":
        pc = settings.get("public_checks", {})
        allowed_types = set(pc.get("allowed_types", []))
        always_allowed = set(pc.get("always_allowed_ids", []))
        violations = {}
        for s in selected:
            if not is_public_allowed(s["source"], sources, allowed_types, always_allowed):
                violations.setdefault(s["source"], []).append(s["title"])
        if violations:
            print("\nPUBLIC CAREER BLOCKED: the following sources are not allowed in a public career")
            print("(Guitar Hero / Rock Band / other game setlists are not allowed; use general customs or YARC content):")
            for src, titles in sorted(violations.items()):
                info = source_info(sources, src)
                label = info["name"] if info else "unknown"
                print(f"  - {src} ({label}): {len(titles)} song(s)")
            print("\nSet visibility to 'private' or restrict source_selection to allowed sources.")
            sys.exit(1)

    if not selected:
        print("\nNo songs selected. Nothing to do.")
        sys.exit(1)

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

    print(f"\nBuilt '{settings.get('career', {}).get('name')}' with {len(selected)} songs across {len(tiers_json)} tiers.")
    print("Per source:")
    for src, n in sorted(breakdown.items(), key=lambda kv: -kv[1]):
        info = source_info(sources, src)
        label = info["name"] if info else "?"
        print(f"  - {src:<14} {n:>4} songs   ({label})")
    for cfg, chunk in filled:
        print(f"  - {cfg['name']:<26} {len(chunk)} songs")
    print(f"\nWrote:\n  {json_path}\n  {preset_path}")


def main():
    parser = argparse.ArgumentParser(description="YARG career builder")
    parser.add_argument("command", choices=["scan", "build"], help="what to do")
    args = parser.parse_args()

    settings = load_settings()
    sources = load_sources()

    if args.command == "scan":
        cmd_scan(settings, sources)
    elif args.command == "build":
        cmd_build(settings, sources)


if __name__ == "__main__":
    main()
