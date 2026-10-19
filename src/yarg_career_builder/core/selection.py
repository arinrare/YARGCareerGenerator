"""Song selection: difficulty sorting and source allocation."""

import random
from collections import Counter, defaultdict


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
        return (0 if d >= 0 else 1, d if d >= 0 else 0)
    return (0 if d >= 0 else 1, -(d if d >= 0 else 0))


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

    random.shuffle(usable)
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
        selected = selected[:target]
        breakdown = dict(Counter(s["source"] for s in selected))

    selected.sort(key=lambda s: difficulty_sort_key(s, ascending))
    return selected, breakdown


def _song_identity(song):
    return (song["artist"], song["title"], song["source"], song["charter"])


def _display_song(song):
    return {
        "artist": song["artist"],
        "title": song["title"],
        "charter": song["charter"],
        "source": song["source"],
    }


def reconcile_setlist(old_setlist, tiers, songs, settings):
    """Reconcile a setlist against a new tier structure.

    Preserves each tier's existing songs (clamped to its new ``song_count``,
    keeping the first N), then fills any remaining slots from ``songs`` in
    difficulty order (easiest first) without repeating a song already present.

    ``old_setlist`` maps tier id -> list of {artist, title, charter, source}.
    ``tiers`` is the current structure (each with ``id`` and ``song_count``).
    Returns a new id -> songs mapping (song entries are normalized display dicts).
    """
    new_setlist = {}
    used = set()

    for t in tiers:
        tid = t["id"]
        count = int(t.get("song_count") or 0)
        kept = [s for s in old_setlist.get(tid, [])][:count]
        new_setlist[tid] = kept
        for s in kept:
            used.add(_song_identity(s))

    needed = {}
    total = 0
    for t in tiers:
        n = int(t.get("song_count") or 0) - len(new_setlist[t["id"]])
        if n > 0:
            needed[t["id"]] = n
            total += n

    if total <= 0 or not songs:
        return new_setlist

    usable, _ = select_and_sort_songs(songs, settings, None)
    remaining = [s for s in usable if _song_identity(s) not in used]
    selected, _ = apply_source_selection(remaining, settings, total)
    pool = selected

    idx = 0
    for t in tiers:
        n = needed.get(t["id"], 0)
        if n > 0:
            new_setlist[t["id"]].extend(_display_song(s) for s in pool[idx:idx + n])
            idx += n

    return new_setlist
