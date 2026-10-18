import json
import zipfile

import yarg_career_builder.core.career_io as career_io


def _career_json():
    return {
        "Name": "Test Career",
        "Title": None,
        "Description": "A description",
        "Source": "yarg",
        "Version": 1,
        "Type": "Career",
        "Tiers": [
            {
                "Name": "Tier A",
                "UnlockCriteria": 0,
                "IsBonus": False,
                "VenueHint": None,
                "CustomUnlockText": None,
                "Songs": [{}, {}, {}],
            },
            {
                "Name": "Tier B",
                "UnlockCriteria": 25,
                "IsBonus": True,
                "VenueHint": "Venue/X",
                "CustomUnlockText": "some text",
                "Songs": [{}] * 5,
            },
        ],
    }


def test_load_career_file_json(tmp_path):
    path = tmp_path / "career.json"
    path.write_text(json.dumps(_career_json()), encoding="utf-8")

    result = career_io.load_career_file(path)

    assert result["career"]["name"] == "Test Career"
    assert result["career"]["description"] == "A description"
    assert result["career"]["source"] == "yarg"

    assert len(result["tiers"]) == 2
    a, b = result["tiers"]
    assert a["name"] == "Tier A"
    assert a["song_count"] == 3
    assert a["unlock_criteria"] == 0
    assert a["is_bonus"] is False
    assert a["venue_hint"] is None

    assert b["song_count"] == 5
    assert b["unlock_criteria"] == 25
    assert b["is_bonus"] is True
    assert b["venue_hint"] == "Venue/X"
    assert b["custom_unlock_text"] == "some text"


def test_load_career_file_preset_zip(tmp_path):
    path = tmp_path / "career.preset"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("preset.json", json.dumps(_career_json()))

    result = career_io.load_career_file(path)
    assert result["career"]["name"] == "Test Career"
    assert len(result["tiers"]) == 2


def test_apply_startup_rule_prefers_existing_career(tmp_path, monkeypatch):
    careers_dir = tmp_path / "careers"
    careers_dir.mkdir()

    career_path = careers_dir / "Saved.json"
    data = _career_json()
    data["Name"] = "Saved Career"
    career_path.write_text(json.dumps(data), encoding="utf-8")

    template_path = tmp_path / "Template.preset"
    with zipfile.ZipFile(template_path, "w") as zf:
        tpl = _career_json()
        tpl["Name"] = "Template Career"
        zf.writestr("preset.json", json.dumps(tpl))

    monkeypatch.setattr(career_io, "CAREERS_DIR", careers_dir)
    monkeypatch.setattr(career_io, "TEMPLATE_PATH", template_path)

    settings = {"loaded_career": "Saved.json"}
    career_io.apply_startup_rule(settings)

    assert settings["career"]["name"] == "Saved Career"


def test_apply_startup_rule_falls_back_to_template(tmp_path, monkeypatch):
    careers_dir = tmp_path / "careers"
    careers_dir.mkdir()

    template_path = tmp_path / "Template.preset"
    with zipfile.ZipFile(template_path, "w") as zf:
        tpl = _career_json()
        tpl["Name"] = "Template Career"
        zf.writestr("preset.json", json.dumps(tpl))

    monkeypatch.setattr(career_io, "CAREERS_DIR", careers_dir)
    monkeypatch.setattr(career_io, "TEMPLATE_PATH", template_path)

    # loaded_career points at a file that no longer exists -> fall back
    settings = {"loaded_career": "Gone.json"}
    career_io.apply_startup_rule(settings)

    assert settings["career"]["name"] == "Template Career"


def test_load_career_file_retains_songs(tmp_path):
    data = _career_json()
    data["Tiers"][0]["Songs"] = [
        {"SongTuple": {"Artist": "A", "Title": "T", "Source": "ghwt", "Charter": "C"}},
        {"SongTuple": None},
        {},
    ]
    path = tmp_path / "career.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = career_io.load_career_file(path)

    assert result["songs"][0] == [{"artist": "A", "title": "T", "charter": "C", "source": "ghwt"}]
    assert result["songs"][1] == []
    assert result["tiers"][0]["id"]


def test_apply_startup_rule_preserves_persisted_tiers():
    settings = {
        "tiers": [
            {"id": "t1", "name": "Kept", "song_count": 3, "unlock_criteria": 0,
             "is_bonus": False, "venue_hint": None, "custom_unlock_text": None},
        ]
    }
    career_io.apply_startup_rule(settings)
    assert settings["tiers"][0]["name"] == "Kept"
    assert settings["setlist"] == {}
