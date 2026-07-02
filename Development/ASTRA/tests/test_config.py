import json

from config.config import Config, DEFAULTS


def test_defaults_when_no_file(tmp_path):
    config = Config(path=tmp_path / "missing.json")
    assert config.name == DEFAULTS["name"]
    assert config.version == DEFAULTS["version"]


def test_loads_values_from_file(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"name": "TestBot", "version": "9.9.9"}), encoding="utf-8")
    config = Config(path=path)
    assert config.name == "TestBot"
    assert config.version == "9.9.9"


def test_partial_file_keeps_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"name": "TestBot"}), encoding="utf-8")
    config = Config(path=path)
    assert config.name == "TestBot"
    assert config.version == DEFAULTS["version"]
