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
    }


def load_career_file(path):
    """Parse a .json or .preset career into {career, tiers}."""
    data = _read_career_json(path)

    career = {
        "name": data.get("Name") or "",
        "title": data.get("Title"),
        "description": data.get("Description"),
        "source": data.get("Source") or "yarg",
        "version": int(data.get("Version") or 1),
        "type": data.get("Type") or "Career",
    }
    tiers = [_tier_to_structure(t) for t in (data.get("Tiers") or [])]
    return {"career": career, "tiers": tiers}


def load_template():
    """Load the current default template into {career, tiers}."""
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
    """Resolve the career structure on startup.

    Load the last-loaded career (if it still exists in the careers folder),
    otherwise fall back to the default template. Mutates and returns ``settings``
    with ``career`` and ``tiers`` populated.
    """
    loaded = settings.get("loaded_career")
    if loaded:
        candidate = CAREERS_DIR / loaded
        if candidate.is_file():
            result = load_career_file(candidate)
            settings["career"] = result["career"]
            settings["tiers"] = result["tiers"]
            return settings

    result = load_template()
    settings["career"] = result["career"]
    settings["tiers"] = result["tiers"]
    return settings
