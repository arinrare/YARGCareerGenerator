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

from ..paths import CAREERS_DIR, TEMPLATE_PATH, BUNDLED_TEMPLATE_PATH


def _read_career_json(path):
    if str(path).lower().endswith(".preset"):
        with zipfile.ZipFile(path, "r") as zf:
            with zf.open("preset.json") as f:
                return json.load(f)
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _tier_to_structure(tier):
    return {
        "name": tier.get("Name") or "",
        "song_count": len(tier.get("Songs") or []),
        "unlock_criteria": int(tier.get("UnlockCriteria") or 0),
        "is_bonus": bool(tier.get("IsBonus", False)),
        "venue_hint": tier.get("VenueHint"),
        "custom_unlock_text": tier.get("CustomUnlockText"),
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
    }
    tiers_data = data.get("Tiers") or []
    tiers = [_tier_to_structure(t) for t in tiers_data]
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
