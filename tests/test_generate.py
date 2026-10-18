import json
import uuid
import zipfile

from yarg_career_builder.core.generate import (
    tuple_id,
    make_song_json,
    make_tier_json,
    make_preset_json,
    sanitize_filename,
    write_outputs,
)


def test_tuple_id_is_deterministic_and_valid_uuid():
    a = tuple_id("Artist", "Title", "ghwt", "Charter")
    b = tuple_id("Artist", "Title", "ghwt", "Charter")
    assert a == b
    uuid.UUID(a)  # raises if invalid


def test_tuple_id_differs_with_inputs():
    assert tuple_id("A", "T", "S", "C") != tuple_id("A", "T", "S", "D")


def test_make_song_json_shape():
    song = {"artist": "A", "title": "T", "source": "ghwt", "charter": "C"}
    out = make_song_json(song)
    assert out["Identifier"] == "SongTuple"
    assert out["SongTuple"] == {"Artist": "A", "Title": "T", "Source": "ghwt", "Charter": "C"}


def test_make_tier_json_shape():
    cfg = {"name": "Tier One", "unlock_criteria": 10, "is_bonus": False}
    out = make_tier_json(cfg, [])
    assert out["Name"] == "Tier One"
    assert out["UnlockCriteria"] == 10
    assert out["IsBonus"] is False
    assert out["UnlockType"] == "StarCount"


def test_make_preset_json_shape():
    career = {"name": "My Career", "type": "Career", "version": 1, "source": "yarg"}
    out = make_preset_json(career, [])
    assert out["Name"] == "My Career"
    assert out["Type"] == "Career"
    assert out["Tiers"] == []


def test_sanitize_filename():
    assert sanitize_filename("My Career: 2026!") == "My_Career_2026"
    assert sanitize_filename("  Hello World  ") == "Hello_World"


def test_write_outputs_creates_json_and_zip(tmp_path):
    preset = {"Name": "Test", "Tiers": []}
    career = {"name": "Test Career"}
    settings = {"output_dir": str(tmp_path)}
    json_path, preset_path = write_outputs(preset, career, settings)

    assert json_path == str(tmp_path / "Test_Career.json")
    assert preset_path == str(tmp_path / "Test_Career.preset")

    with open(json_path, "r", encoding="utf-8") as f:
        assert json.load(f)["Name"] == "Test"

    with zipfile.ZipFile(preset_path) as zf:
        assert zf.namelist() == ["preset.json"]
        with zf.open("preset.json") as f:
            assert json.load(f)["Name"] == "Test"
