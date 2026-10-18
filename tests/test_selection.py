from yarg_career_builder.core.selection import (
    difficulty_value,
    select_and_sort_songs,
    allocate_sources,
    apply_source_selection,
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
