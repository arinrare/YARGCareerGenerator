import pytest

from yarg_career_builder.core.scan import parse_ini, scan_library


def _write_ini(path, text):
    path.write_text(text, encoding="utf-8")


def test_parse_ini_reads_keys_and_strips_quotes(tmp_path):
    ini = tmp_path / "song.ini"
    _write_ini(
        ini,
        "[song]\n"
        'name = "My Song"\n'
        "artist = The Artist\n"
        "icon = 'ghwt'\n"
        "charter = Neversoft\n",
    )
    data = parse_ini(str(ini))
    assert data["name"] == "My Song"
    assert data["artist"] == "The Artist"
    assert data["icon"] == "ghwt"
    assert data["charter"] == "Neversoft"


def test_parse_ini_skips_comments_and_blank_lines(tmp_path):
    ini = tmp_path / "song.ini"
    _write_ini(
        ini,
        "; a comment\n"
        "# another comment\n"
        "\n"
        "name = Song\n",
    )
    data = parse_ini(str(ini))
    assert data["name"] == "Song"
    assert ";" not in data


def test_scan_library_finds_song_folders(tmp_path):
    lib = tmp_path / "lib"
    song_dir = lib / "Artist" / "Song"
    song_dir.mkdir(parents=True)
    _write_ini(
        song_dir / "song.ini",
        "[song]\nname = Song\nartist = Artist\ncharter = Charter\nicon = ghwt\n",
    )
    (lib / "empty_folder").mkdir(parents=True)

    songs = scan_library(str(lib))
    assert len(songs) == 1
    s = songs[0]
    assert s["title"] == "Song"
    assert s["artist"] == "Artist"
    assert s["charter"] == "Charter"
    assert s["source"] == "ghwt"
    assert s["folder"] == str(song_dir)


def test_scan_library_uses_frets_fallback_for_charter(tmp_path):
    lib = tmp_path / "lib"
    song_dir = lib / "Song"
    song_dir.mkdir(parents=True)
    _write_ini(
        song_dir / "song.ini",
        "[song]\nname = Song\nartist = Artist\nfrets = SomeCharter\nicon = ghwt\n",
    )
    songs = scan_library(str(lib))
    assert songs[0]["charter"] == "SomeCharter"


def test_scan_library_missing_root_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        scan_library(str(tmp_path / "does_not_exist"))
