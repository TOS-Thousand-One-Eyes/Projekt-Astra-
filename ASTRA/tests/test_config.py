import json

from config.config import Config, DEFAULTS, UNKNOWN_VERSION


def test_defaults_when_no_file(tmp_path):
    config = Config(path=tmp_path / "missing.json")
    assert config.name == DEFAULTS["name"]


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
    assert config.log_level == DEFAULTS["log_level"]


def test_version_falls_back_to_unknown_sentinel_when_missing_from_file(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"name": "TestBot"}), encoding="utf-8")
    config = Config(path=path)
    assert config.version == UNKNOWN_VERSION


def test_version_falls_back_to_unknown_sentinel_when_no_file(tmp_path):
    config = Config(path=tmp_path / "missing.json")
    assert config.version == UNKNOWN_VERSION


def test_version_falls_back_to_unknown_sentinel_when_null_in_file(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"name": "TestBot", "version": None}), encoding="utf-8")
    config = Config(path=path)
    assert config.version == UNKNOWN_VERSION


def test_log_level_and_log_to_file_defaults(tmp_path):
    config = Config(path=tmp_path / "missing.json")
    assert config.log_level == DEFAULTS["log_level"]
    assert config.log_to_file == DEFAULTS["log_to_file"]


def test_loads_log_settings_from_file(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"log_level": "DEBUG", "log_to_file": True}), encoding="utf-8")
    config = Config(path=path)
    assert config.log_level == "DEBUG"
    assert config.log_to_file is True


def test_check_for_updates_default(tmp_path):
    config = Config(path=tmp_path / "missing.json")
    assert config.check_for_updates == DEFAULTS["check_for_updates"]


def test_loads_check_for_updates_from_file(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"check_for_updates": False}), encoding="utf-8")
    config = Config(path=path)
    assert config.check_for_updates is False


def test_malformed_json_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not valid json", encoding="utf-8")
    config = Config(path=path)
    assert config.name == DEFAULTS["name"]
    assert config.version == UNKNOWN_VERSION
