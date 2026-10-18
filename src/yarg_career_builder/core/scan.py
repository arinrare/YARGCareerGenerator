"""Music library scanning and song.ini parsing."""

import os

# song.ini keys used to build a Song Tuple
KEY_NAME = "name"
KEY_ARTIST = "artist"
KEY_CHARTER = "charter"
KEY_CHARTER_FALLBACK = "frets"
KEY_SOURCE = "icon"


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
        raise FileNotFoundError(f"music_root does not exist: {music_root}")

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
