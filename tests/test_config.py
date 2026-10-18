import json

from yarg_career_builder.core.config import load_json


def test_load_json_handles_utf8_bom(tmp_path):
    p = tmp_path / "data.json"
    p.write_bytes(b"\xef\xbb\xbf" + json.dumps({"a": 1}).encode("utf-8"))
    assert load_json(p) == {"a": 1}
