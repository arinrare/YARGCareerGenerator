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

    return json_path, preset_path
