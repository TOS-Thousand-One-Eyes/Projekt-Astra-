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
    assert config.load_warnings == []


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


def test_language_fallback_defaults(tmp_path):
    config = Config(path=tmp_path / "missing.json")
    assert config.use_language_fallback == DEFAULTS["use_language_fallback"]
    assert config.language_base_url == DEFAULTS["language_base_url"]
    assert config.language_model == DEFAULTS["language_model"]
    assert config.language_generate_timeout == DEFAULTS["language_generate_timeout"]


def test_loads_language_fallback_settings_from_file(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "use_language_fallback": True,
                "language_base_url": "http://127.0.0.1:11434",
                "language_model": "qwen3:8b",
                "language_generate_timeout": 90,
            }
        ),
        encoding="utf-8",
    )
    config = Config(path=path)
    assert config.use_language_fallback is True
    assert config.language_base_url == "http://127.0.0.1:11434"
    assert config.language_model == "qwen3:8b"
    assert config.language_generate_timeout == 90


def test_malformed_json_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not valid json", encoding="utf-8")
    config = Config(path=path)
    assert config.name == DEFAULTS["name"]
    assert config.version == UNKNOWN_VERSION


def test_malformed_json_produces_a_load_warning(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not valid json", encoding="utf-8")
    config = Config(path=path)
    assert any("not valid JSON" in warning for warning in config.load_warnings)


def test_valid_json_that_is_not_an_object_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("null", encoding="utf-8")
    config = Config(path=path)
    assert config.name == DEFAULTS["name"]
    assert config.version == UNKNOWN_VERSION


def test_valid_json_that_is_not_an_object_produces_a_load_warning(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("null", encoding="utf-8")
    config = Config(path=path)
    assert any("does not contain a JSON object" in warning for warning in config.load_warnings)


def test_missing_version_produces_a_load_warning(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"name": "TestBot"}), encoding="utf-8")
    config = Config(path=path)
    assert any("version" in warning for warning in config.load_warnings)


def test_present_version_produces_no_load_warning(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"name": "TestBot", "version": "1.2.3"}), encoding="utf-8")
    config = Config(path=path)
    assert config.load_warnings == []


def test_string_false_for_boolean_setting_keeps_the_default(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"use_language_fallback": "false"}), encoding="utf-8")
    config = Config(path=path)
    assert config.use_language_fallback is False


def test_string_false_for_boolean_setting_produces_a_load_warning(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"use_language_fallback": "false"}), encoding="utf-8")
    config = Config(path=path)
    assert any("use_language_fallback" in warning for warning in config.load_warnings)


def test_non_numeric_timeout_keeps_the_default_and_warns(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"language_generate_timeout": "240"}), encoding="utf-8")
    config = Config(path=path)
    assert config.language_generate_timeout == DEFAULTS["language_generate_timeout"]
    assert any("language_generate_timeout" in warning for warning in config.load_warnings)


def test_boolean_timeout_keeps_the_default_and_warns(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"language_generate_timeout": True}), encoding="utf-8")
    config = Config(path=path)
    assert config.language_generate_timeout == DEFAULTS["language_generate_timeout"]
    assert any("language_generate_timeout" in warning for warning in config.load_warnings)


def test_float_timeout_is_accepted(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"language_generate_timeout": 90.5, "version": "1.2.3"}), encoding="utf-8")
    config = Config(path=path)
    assert config.language_generate_timeout == 90.5
    assert config.load_warnings == []


def test_non_string_name_keeps_the_default_and_warns(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"name": 42}), encoding="utf-8")
    config = Config(path=path)
    assert config.name == DEFAULTS["name"]
    assert any('"name"' in warning for warning in config.load_warnings)


def test_non_utf8_config_file_falls_back_to_defaults_with_a_warning(tmp_path):
    path = tmp_path / "config.json"
    path.write_bytes('{"name": "TestBot", "version": "1.0.0"}'.encode("utf-16"))
    config = Config(path=path)
    assert config.name == DEFAULTS["name"]
    assert any("UTF-8" in warning for warning in config.load_warnings)
