"""Tier distribution: splitting a song total across tiers."""


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
