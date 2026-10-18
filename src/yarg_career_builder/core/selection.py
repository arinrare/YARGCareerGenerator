"""Song selection: difficulty sorting and source allocation."""

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
