from yarg_career_builder.core.sources import merged_source_rows


def test_merged_source_rows_unions_registry_and_counts():
    sources = {
        "ghwt": {"name": "Guitar Hero: World Tour", "type": "gh"},
        "gh3": {"name": "Guitar Hero III", "type": "gh"},
        "yarg": {"name": "YARG", "type": "game"},
    }
    counts = {"ghwt": 86, "unknown_src": 3}

    rows = merged_source_rows(sources, counts, ["custom", "charter"], ["yarg"])

    by_id = {r["source"]: r for r in rows}

    # registry-only source present with count 0
    assert by_id["gh3"]["count"] == 0
    assert by_id["gh3"]["name"] == "Guitar Hero III"

    # in-library source has its count
    assert by_id["ghwt"]["count"] == 86

    # scan source missing from the registry is still included
    assert by_id["unknown_src"]["name"] == "?"
    assert by_id["unknown_src"]["count"] == 3

    # public flag respected
    assert by_id["yarg"]["public"] is True
    assert by_id["ghwt"]["public"] is False

    # library sources (count > 0) sort before registry-only (count 0)
    first_half = rows[:2]
    assert all(r["count"] > 0 for r in first_half)
