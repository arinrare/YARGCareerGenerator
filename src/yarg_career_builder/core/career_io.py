"""Career structure I/O: load a career or the default template.

A "career" is a YARG preset export — either a plain ``.json`` or a zipped
``.preset`` (containing ``preset.json``). We only care about its *structure*
(tiers + career metadata), not the concrete songs, so loading extracts:

- career metadata: name, title, description, source, version, type.
- tiers: name, song_count (number of songs), unlock_criteria, is_bonus,
  venue_hint, custom_unlock_text.
"""

import json
import os
import shutil
import uuid
import zipfile

from .. import paths
from ..paths import CAREERS_DIR, TEMPLATE_PATH, BUNDLED_TEMPLATE_PATH, media_dir_for


def _read_career_json(path):
    if str(path).lower().endswith(".preset"):
        with zipfile.ZipFile(path, "r") as zf:
            with zf.open("preset.json") as f:
                return json.load(f)
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _tier_to_structure(tier, media_map=None):
    media_map = media_map or {}
    media_filename = tier.get("MediaFilename")
    return {
        "name": tier.get("Name") or "",
        "description": tier.get("Description"),
        "song_count": len(tier.get("Songs") or []),
        "unlock_type": tier.get("UnlockType") or "StarCount",
        "unlock_criteria": int(tier.get("UnlockCriteria") or 0),
        "is_bonus": bool(tier.get("IsBonus", False)),
        "venue_size": tier.get("VenueSize") or "NotSpecified",
        "venue_hint": tier.get("VenueHint"),
        "completion_mode": tier.get("CompletionMode") or "SingleSong",
        "custom_unlock_text": tier.get("CustomUnlockText"),
        "completion_bonus": tier.get("CompletionBonus") or "None",
        "completion_bonus_text": tier.get("CompletionBonusText"),
        "media_path": media_map.get(media_filename) if media_filename else None,
        "id": tier.get("Id") or str(uuid.uuid4()),
    }


def _song_to_dict(entry):
    tup = entry.get("SongTuple") or {}
    artist = (tup.get("Artist") or "").strip()
    title = (tup.get("Title") or "").strip()
    source = (tup.get("Source") or "").strip()
    charter = (tup.get("Charter") or "").strip()
    if not (artist and title and source and charter):
        return None
    return {"artist": artist, "title": title, "charter": charter, "source": source}


def _tier_songs(tier):
    songs = []
    for entry in (tier.get("Songs") or []):
        song = _song_to_dict(entry)
        if song:
            songs.append(song)
    return songs


def _setlist_from_songs(tiers, songs):
    return {t["id"]: list(songs[i]) for i, t in enumerate(tiers)}


def _extract_media(path, media_dir):
    """Extract embedded media files from a .preset into ``media_dir``.

    Returns a mapping of ``filename -> extracted path``. Plain ``.json`` files
    cannot carry media, so an empty mapping is returned for them.
    """
    if not str(path).lower().endswith(".preset"):
        return {}
    media_map = {}
    with zipfile.ZipFile(path, "r") as zf:
        for entry in zf.namelist():
            if entry == "preset.json":
                continue
            basename = os.path.basename(entry)
            if not basename:
                continue
            os.makedirs(media_dir, exist_ok=True)
            dest = os.path.join(str(media_dir), basename)
            with zf.open(entry) as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)
            media_map[basename] = dest
    return media_map


def load_career_file(path):
    """Parse a .json or .preset career into {career, tiers, songs}."""
    data = _read_career_json(path)

    career = {
        "name": data.get("Name") or "",
        "title": data.get("Title"),
        "description": data.get("Description"),
        "source": data.get("Source") or "yarg",
        "version": int(data.get("Version") or 1),
        "type": data.get("Type") or "Career",
        "id": data.get("Id") or str(uuid.uuid4()),
    }
    media_map = _extract_media(path, media_dir_for(career))

    tiers_data = data.get("Tiers") or []
    tiers = [_tier_to_structure(t, media_map) for t in tiers_data]
    songs = [_tier_songs(t) for t in tiers_data]
    return {"career": career, "tiers": tiers, "songs": songs}


def load_template():
    """Load the current default template into {career, tiers, songs}."""
    if not os.path.isfile(TEMPLATE_PATH):
        raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}")
    return load_career_file(TEMPLATE_PATH)


def seed_template():
    """Copy the bundled template to TEMPLATE_PATH if it does not exist yet."""
    if os.path.isfile(TEMPLATE_PATH):
        return TEMPLATE_PATH
    if os.path.isfile(BUNDLED_TEMPLATE_PATH):
        os.makedirs(os.path.dirname(TEMPLATE_PATH), exist_ok=True)
        shutil.copyfile(BUNDLED_TEMPLATE_PATH, TEMPLATE_PATH)
    return TEMPLATE_PATH


def import_template(source_path):
    """Replace the template with a user-supplied YARG export."""
    os.makedirs(os.path.dirname(TEMPLATE_PATH), exist_ok=True)
    shutil.copyfile(source_path, TEMPLATE_PATH)
    return TEMPLATE_PATH


def apply_startup_rule(settings):
    """Ensure the career structure and setlist are populated on startup.

    A structure persisted by a previous session (``tiers`` present) is kept
    as-is, so in-session tier edits and the reconciled setlist survive a
    restart. Otherwise the structure is seeded from the last loaded/built
    career, falling back to the default template. Mutates and returns
    ``settings`` with ``career``, ``tiers`` and ``setlist`` populated.
    """
    if settings.get("tiers"):
        settings.setdefault("setlist", {})
        return settings

    result = None
    loaded = settings.get("loaded_career")
    if loaded:
        candidate = CAREERS_DIR / loaded
        if candidate.is_file():
            result = load_career_file(candidate)

    if result is None:
        result = load_template()

    settings["career"] = result["career"]
    settings["tiers"] = result["tiers"]
    settings["setlist"] = _setlist_from_songs(result["tiers"], result["songs"])
    return settings


# ---------------------------------------------------------------------- #
#  Media lifecycle
# ---------------------------------------------------------------------- #

def reconcile_media(career, tiers):
    """Delete files in a career's media folder that no tier references.

    Called after the tier structure changes (clear/replace/remove media or a
    tier) to keep ``media/<id>/`` a mirror of the currently-referenced files.
    Removes the folder itself when it becomes empty.
    """
    d = media_dir_for(career)
    if not os.path.isdir(d):
        return
    d_abs = os.path.abspath(str(d))
    referenced = set()
    for t in tiers:
        p = t.get("media_path")
        if p and os.path.dirname(os.path.abspath(p)) == d_abs:
            referenced.add(os.path.basename(p))
    for name in os.listdir(str(d)):
        if name not in referenced:
            try:
                os.remove(os.path.join(str(d), name))
            except OSError:
                pass
    try:
        if not os.listdir(str(d)):
            os.rmdir(str(d))
    except OSError:
        pass


# ---------------------------------------------------------------------- #
#  Career management (list / delete / cleanup)
# ---------------------------------------------------------------------- #

def _career_files(out_dir):
    """Map of stem -> {"json": name|None, "preset": name|None} in ``out_dir``."""
    stems = {}
    if not os.path.isdir(out_dir):
        return stems
    for name in os.listdir(out_dir):
        lower = name.lower()
        if lower.endswith(".json"):
            stems.setdefault(name[:-5], {})["json"] = name
        elif lower.endswith(".preset"):
            stems.setdefault(name[:-7], {})["preset"] = name
    return stems


def _career_ids(out_dir):
    """Map of stem -> Id string for every career file in ``out_dir``."""
    ids = {}
    for stem, files in _career_files(out_dir).items():
        for key in ("json", "preset"):
            name = files.get(key)
            if not name:
                continue
            try:
                data = _read_career_json(os.path.join(out_dir, name))
                if data.get("Id"):
                    ids[stem] = str(data["Id"])
                    break
            except Exception:
                continue
    return ids


def scan_careers(out_dir):
    """List careers in ``out_dir`` with metadata for a management view."""
    records = []
    for stem, files in sorted(_career_files(out_dir).items()):
        record = {
            "stem": stem,
            "name": stem,
            "json": files.get("json"),
            "preset": files.get("preset"),
            "id": None,
            "media_dir": None,
            "has_media": False,
            "tier_count": 0,
            "song_count": 0,
        }
        path = None
        for key in ("json", "preset"):
            name = files.get(key)
            if name:
                path = os.path.join(out_dir, name)
                break
        if path:
            try:
                data = _read_career_json(path)
            except Exception:
                data = None
            if data:
                record["name"] = data.get("Name") or stem
                record["id"] = data.get("Id")
                tiers = data.get("Tiers") or []
                record["tier_count"] = len(tiers)
                record["song_count"] = sum(len(t.get("Songs") or []) for t in tiers)
        if record["id"]:
            md = paths.MEDIA_DIR / str(record["id"])
            record["media_dir"] = str(md)
            record["has_media"] = os.path.isdir(md) and any(
                os.path.isfile(os.path.join(str(md), f)) for f in os.listdir(str(md))
            )
        records.append(record)
    return records


def _remove_media_dir(cid):
    d = paths.MEDIA_DIR / str(cid)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
        return str(d)
    return None


def delete_career(out_dir, stem):
    """Delete a career's .json/.preset and, if now orphaned, its media folder.

    The media folder is only removed once no remaining career file references
    the same Id (so rename-produced duplicates sharing one Id stay intact).
    """
    career_id = None
    removed_files = []
    for name in (f"{stem}.json", f"{stem}.preset"):
        p = os.path.join(out_dir, name)
        if os.path.isfile(p):
            try:
                data = _read_career_json(p)
                career_id = data.get("Id") or career_id
            except Exception:
                pass
            os.remove(p)
            removed_files.append(p)

    media_removed = None
    if career_id:
        remaining = set(_career_ids(out_dir).values())
        if str(career_id) not in remaining:
            media_removed = _remove_media_dir(str(career_id))

    return {"files": removed_files, "media": media_removed, "id": career_id}


def find_unused_media(out_dir):
    """Media folders whose career Id no longer exists in ``out_dir``."""
    referenced = set(_career_ids(out_dir).values())
    unused = []
    if os.path.isdir(paths.MEDIA_DIR):
        for name in os.listdir(str(paths.MEDIA_DIR)):
            if name in referenced:
                continue
            d = os.path.join(str(paths.MEDIA_DIR), name)
            if os.path.isdir(d):
                unused.append(d)
    return unused


def clean_unused_media(out_dir):
    """Delete media folders for careers that no longer exist in ``out_dir``."""
    removed = []
    for d in find_unused_media(out_dir):
        shutil.rmtree(d, ignore_errors=True)
        removed.append(d)
    return removed
