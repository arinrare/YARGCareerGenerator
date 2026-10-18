from yarg_career_builder.core.selection import (
    difficulty_value,
    select_and_sort_songs,
    allocate_sources,
    apply_source_selection,
    reconcile_setlist,
)


def _song(title, source="ghwt", diff=3, artist="A", charter="C"):
    return {
        "title": title,
        "artist": artist,
        "charter": charter,
        "source": source,
        "ini": {"diff_guitar": str(diff)},
    }


def _settings(**overrides):
    s = {
        "difficulty": {"field": "diff_guitar", "ascending": True, "missing": "last"},
        "source_selection": {"weights": {}, "filter": [], "limit": 0},
    }
    s.update(overrides)
    return s


def test_difficulty_value_reads_field():
    assert difficulty_value(_song("x", diff=4), _settings()) == 4


def test_difficulty_value_missing_is_negative():
    song = _song("x")
    song["ini"] = {}
    assert difficulty_value(song, _settings()) == -1


def test_select_and_sort_songs_sorts_ascending_and_excludes_bad_meta():
    songs = [
        _song("Hard", diff=7),
        _song("Easy", diff=1),
        _song("Mid", diff=4),
        # missing metadata -> excluded
        {"title": "", "artist": "A", "charter": "C", "source": "ghwt", "ini": {}},
    ]
    usable, excluded = select_and_sort_songs(songs, _settings(), {})
    assert [s["title"] for s in usable] == ["Easy", "Mid", "Hard"]
    assert len(excluded["missing_meta"]) == 1


def test_select_and_sort_songs_missing_skip_mode():
    songs = [_song("NoDiff", diff=-1), _song("Has", diff=2)]
    usable, excluded = select_and_sort_songs(songs, _settings(), {})
    # 'last' is default, so both stay
    assert len(usable) == 2

    settings = _settings()
    settings["difficulty"]["missing"] = "skip"
    usable, excluded = select_and_sort_songs(songs, settings, {})
    assert [s["title"] for s in usable] == ["Has"]
    assert len(excluded["no_guitar"]) == 1


def test_allocate_sources_proportional_and_clamped():
    available = {"a": 100, "b": 100, "c": 2}
    takes = allocate_sources({"a": 1, "b": 1, "c": 1}, 60, available)
    assert takes["a"] + takes["b"] + takes["c"] == 60
    assert takes["c"] <= 2


def test_allocate_sources_empty_weights():
    assert allocate_sources({}, 10, {"a": 10}) == {}


def test_apply_source_selection_filter_mode():
    songs = [_song("a1", source="ghwt"), _song("b1", source="gh3"), _song("a2", source="ghwt")]
    settings = _settings()
    for s in songs:
        s["difficulty"] = difficulty_value(s, settings)
    songs.sort(key=lambda s: s["title"])
    settings["source_selection"]["filter"] = ["ghwt"]
    selected, breakdown = apply_source_selection(songs, settings, 10)
    assert {s["source"] for s in selected} == {"ghwt"}
    assert breakdown == {"ghwt": 2}


def test_apply_source_selection_weights_mode():
    songs = [_song("a1", source="ghwt"), _song("b1", source="gh3")]
    settings = _settings()
    for s in songs:
        s["difficulty"] = difficulty_value(s, settings)
    songs.sort(key=lambda s: s["title"])
    settings["source_selection"]["weights"] = {"ghwt": 3, "gh3": 1}
    selected, breakdown = apply_source_selection(songs, settings, 4)
    # both sources exhausted (1 each available), weights clamp
    assert len(selected) == 2
    assert breakdown == {"ghwt": 1, "gh3": 1}


def test_apply_source_selection_filter_mode_caps_to_target():
    songs = [_song(f"s{i}", diff=i, source="ghwt") for i in range(10)]
    settings = _settings()
    for s in songs:
        s["difficulty"] = difficulty_value(s, settings)
    songs.sort(key=lambda s: s["title"])

    selected, _ = apply_source_selection(songs, settings, 4)
    # filter mode with no filter/limit must respect the tier total (4), easiest first
    assert [s["title"] for s in selected] == ["s0", "s1", "s2", "s3"]


def _disp(title, source="ghwt", artist="A", charter="C"):
    return {"artist": artist, "title": title, "charter": charter, "source": source}


def test_reconcile_setlist_preserves_and_clamps():
    settings = _settings()
    old = {
        "t1": [_disp("a"), _disp("b"), _disp("c")],
        "t2": [_disp("d")],
    }
    tiers = [
        {"id": "t1", "song_count": 2},
        {"id": "t2", "song_count": 1},
        {"id": "t3", "song_count": 0},
    ]
    new = reconcile_setlist(old, tiers, [], settings)
    assert [s["title"] for s in new["t1"]] == ["a", "b"]
    assert [s["title"] for s in new["t2"]] == ["d"]
    assert new["t3"] == []


def test_reconcile_setlist_fills_gaps_without_repeats():
    settings = _settings()
    old = {"t1": [_disp("pinned")]}
    tiers = [{"id": "t1", "song_count": 3}]
    songs = [
        _song("pinned", diff=1),  # already in setlist -> excluded
        _song("easy", diff=2),
        _song("mid", diff=4),
        _song("hard", diff=7),
    ]
    new = reconcile_setlist(old, tiers, songs, settings)
    assert [s["title"] for s in new["t1"]] == ["pinned", "easy", "mid"]


def test_reconcile_setlist_fills_weighted_from_remaining():
    settings = _settings()
    settings["source_selection"]["weights"] = {"ghwt": 1}
    old = {"t1": [_disp(f"t{i}") for i in range(3)]}
    tiers = [
        {"id": "t1", "song_count": 3},
        {"id": "t2", "song_count": 2},
    ]
    songs = [_song(f"t{i}", diff=i, source="ghwt") for i in range(6)]
    new = reconcile_setlist(old, tiers, songs, settings)
    # new tier filled from remaining (unused) ghwt songs, easiest first
    assert [s["title"] for s in new["t2"]] == ["t3", "t4"]
