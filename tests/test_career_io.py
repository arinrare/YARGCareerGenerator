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
    assert a["unlock_type"] == "StarCount"
    assert a["venue_size"] == "NotSpecified"
    assert a["completion_mode"] == "SingleSong"
    assert a["completion_bonus"] == "None"
    assert a["media_path"] is None

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


def test_load_career_file_preset_extracts_media(tmp_path, monkeypatch):
    media_dir = tmp_path / "media"
    monkeypatch.setattr(career_io.paths, "MEDIA_DIR", media_dir)

    data = _career_json()
    data["Id"] = "career-id-1234"
    data["Tiers"][0]["MediaFilename"] = "art.png"
    data["Tiers"][0]["CompletionBonus"] = "Image"

    path = tmp_path / "career.preset"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("preset.json", json.dumps(data))
        zf.writestr("art.png", b"fake-image-bytes")

    result = career_io.load_career_file(path)
    assert result["career"]["id"] == "career-id-1234"
    assert result["tiers"][0]["completion_bonus"] == "Image"
    assert result["tiers"][0]["media_path"] == str(media_dir / "career-id-1234" / "art.png")
    assert (media_dir / "career-id-1234" / "art.png").read_bytes() == b"fake-image-bytes"


def test_load_career_file_preserves_id(tmp_path):
    data = _career_json()
    data["Id"] = "preset-id-999"
    path = tmp_path / "career.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = career_io.load_career_file(path)
    assert result["career"]["id"] == "preset-id-999"


def test_two_careers_do_not_collide_media(tmp_path, monkeypatch):
    media_dir = tmp_path / "media"
    monkeypatch.setattr(career_io.paths, "MEDIA_DIR", media_dir)

    for cid, payload in (("id-a", b"bytes-a"), ("id-b", b"bytes-b")):
        data = _career_json()
        data["Id"] = cid
        data["Tiers"][0]["MediaFilename"] = "art.png"
        data["Tiers"][0]["CompletionBonus"] = "Image"
        path = tmp_path / f"{cid}.preset"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("preset.json", json.dumps(data))
            zf.writestr("art.png", payload)
        career_io.load_career_file(path)

    assert (media_dir / "id-a" / "art.png").read_bytes() == b"bytes-a"
    assert (media_dir / "id-b" / "art.png").read_bytes() == b"bytes-b"


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


def test_scan_careers_reads_metadata(tmp_path, monkeypatch):
    media_dir = tmp_path / "media"
    monkeypatch.setattr(career_io.paths, "MEDIA_DIR", media_dir)

    out = tmp_path / "careers"
    out.mkdir()
    data = _career_json()
    data["Id"] = "id-1"
    data["Name"] = "My Tour"
    (out / "My_Tour.json").write_text(json.dumps(data), encoding="utf-8")
    (out / "My_Tour.preset").write_bytes(b"zip")

    records = career_io.scan_careers(str(out))
    assert len(records) == 1
    r = records[0]
    assert r["stem"] == "My_Tour"
    assert r["name"] == "My Tour"
    assert r["json"] == "My_Tour.json"
    assert r["preset"] == "My_Tour.preset"
    assert r["id"] == "id-1"
    assert r["tier_count"] == 2
    assert r["song_count"] == 8
    assert r["has_media"] is False


def test_delete_career_removes_files_and_media(tmp_path, monkeypatch):
    media_dir = tmp_path / "media"
    monkeypatch.setattr(career_io.paths, "MEDIA_DIR", media_dir)

    out = tmp_path / "careers"
    out.mkdir()
    data = _career_json()
    data["Id"] = "id-1"
    (out / "My_Tour.json").write_text(json.dumps(data), encoding="utf-8")
    (out / "My_Tour.preset").write_bytes(b"zip")

    md = media_dir / "id-1"
    md.mkdir(parents=True)
    (md / "art.png").write_bytes(b"x")

    result = career_io.delete_career(str(out), "My_Tour")
    assert not (out / "My_Tour.json").exists()
    assert not (out / "My_Tour.preset").exists()
    assert result["id"] == "id-1"
    assert result["media"] == str(md)
    assert not md.exists()


def test_delete_career_keeps_shared_media(tmp_path, monkeypatch):
    media_dir = tmp_path / "media"
    monkeypatch.setattr(career_io.paths, "MEDIA_DIR", media_dir)

    out = tmp_path / "careers"
    out.mkdir()
    data = _career_json()
    data["Id"] = "id-1"
    (out / "Old_Name.json").write_text(json.dumps(data), encoding="utf-8")
    (out / "New_Name.json").write_text(json.dumps(data), encoding="utf-8")

    md = media_dir / "id-1"
    md.mkdir(parents=True)
    (md / "art.png").write_bytes(b"x")

    result = career_io.delete_career(str(out), "Old_Name")
    assert result["media"] is None
    assert md.exists()


def test_clean_unused_media(tmp_path, monkeypatch):
    media_dir = tmp_path / "media"
    monkeypatch.setattr(career_io.paths, "MEDIA_DIR", media_dir)

    out = tmp_path / "careers"
    out.mkdir()
    data = _career_json()
    data["Id"] = "id-live"
    (out / "Live.json").write_text(json.dumps(data), encoding="utf-8")

    (media_dir / "id-live").mkdir(parents=True)
    (media_dir / "id-orphan").mkdir(parents=True)

    removed = career_io.clean_unused_media(str(out))
    assert str(media_dir / "id-orphan") in removed
    assert (media_dir / "id-live").exists()
    assert not (media_dir / "id-orphan").exists()


def test_reconcile_media_removes_unreferenced(tmp_path, monkeypatch):
    media_dir = tmp_path / "media"
    monkeypatch.setattr(career_io.paths, "MEDIA_DIR", media_dir)

    career = {"id": "id-1"}
    md = media_dir / "id-1"
    md.mkdir(parents=True)
    (md / "keep.png").write_bytes(b"x")
    (md / "drop.png").write_bytes(b"x")

    tiers = [{"media_path": str(md / "keep.png")}]
    career_io.reconcile_media(career, tiers)

    assert (md / "keep.png").exists()
    assert not (md / "drop.png").exists()
