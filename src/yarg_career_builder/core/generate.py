"""Output generation: Song Tuple / tier / preset JSON and .preset zip writing."""

import hashlib
import json
import os
import uuid
import zipfile

from ..paths import CAREERS_DIR


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


def _media_filename(tier_cfg):
    if tier_cfg.get("completion_bonus") not in ("Image", "Sound", "Video"):
        return None
    path = tier_cfg.get("media_path")
    return os.path.basename(path) if path else None


def make_tier_json(tier_cfg, songs):
    return {
        "Name": tier_cfg["name"],
        "Id": tier_cfg.get("id") or str(uuid.uuid4()),
        "Description": tier_cfg.get("description"),
        "Songs": [make_song_json(s) for s in songs],
        "CustomUnlockText": tier_cfg.get("custom_unlock_text"),
        "BackgroundImage": None,
        "CompletionBonusText": tier_cfg.get("completion_bonus_text"),
        "CompletionBonus": tier_cfg.get("completion_bonus") or "None",
        "MediaFilename": _media_filename(tier_cfg),
        "VenueSize": tier_cfg.get("venue_size") or "NotSpecified",
        "VenueHint": tier_cfg.get("venue_hint"),
        "UnlockType": tier_cfg.get("unlock_type") or "StarCount",
        "UnlockCriteria": int(tier_cfg.get("unlock_criteria", 0)),
        "CompletionMode": tier_cfg.get("completion_mode") or "SingleSong",
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
        "Id": career.get("id") or str(uuid.uuid4()),
        "Type": career.get("type", "Career"),
        "Tiers": tiers,
    }


def sanitize_filename(name):
    keep = []
    for ch in name:
        if ch.isalnum() or ch in "-_ ":
            keep.append(ch)
    return "".join(keep).strip().replace(" ", "_")


def write_outputs(preset, career, settings, media_files=None):
    out_dir = settings.get("output_dir") or CAREERS_DIR
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
        _write_media_files(zf, media_files)

    return json_path, preset_path


def _write_media_files(zf, media_files):
    """Embed referenced completion-bonus media into the .preset archive."""
    exported = set()
    for path in media_files or []:
        if not path or not os.path.isfile(path):
            continue
        filename = os.path.basename(path)
        if filename in exported:
            continue
        zf.write(path, arcname=filename)
        exported.add(filename)
