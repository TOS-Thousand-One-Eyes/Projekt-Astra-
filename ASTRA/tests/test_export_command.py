import json

from commands.export_command import ExportCommand


def test_export_creates_file_with_current_config_and_memory(config, memory, tmp_path):
    memory.learn("name", "Erik")
    memory.remember("buy milk")
    export = ExportCommand(config, memory, export_dir=tmp_path / "exports")
    export.handle("export", "export")
    files = list((tmp_path / "exports").glob("astra_export_*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert "exported_at" in data
    expected_keys = {
        "name", "version", "log_level", "log_to_file", "check_for_updates",
        "gui_theme", "use_language_fallback", "language_base_url", "language_model",
        "language_generate_timeout", "language_num_ctx", "language_temperature",
        "language_keep_alive", "use_vision_model", "vision_base_url", "vision_model",
        "vision_generate_timeout", "vision_num_ctx", "self_learning_mode",
        "screen_observer_enabled", "screen_observer_poll_seconds",
        "screen_observer_min_analysis_interval", "screen_observer_change_threshold",
        "screen_observer_notify_threshold", "screen_observer_notification_cooldown",
    }
    assert set(data["config"]) == expected_keys
    for key in expected_keys:
        assert data["config"][key] == getattr(config, key)
    assert data["facts"] == {"name": "Erik"}
    assert data["long_memory"][0]["entry"] == "buy milk"


def test_export_response_mentions_exported_file(config, memory, tmp_path):
    export_dir = tmp_path / "exports"
    response = ExportCommand(config, memory, export_dir=export_dir).handle("export", "export")
    assert "Exported" in response
    assert str(export_dir) in response


def test_export_ignores_unrelated_messages(config, memory, tmp_path):
    export_dir = tmp_path / "exports"
    export = ExportCommand(config, memory, export_dir=export_dir)
    assert export.handle("hello", "hello") is None
    assert not export_dir.exists()


def test_two_exports_do_not_overwrite_each_other(config, memory, tmp_path):
    export = ExportCommand(config, memory, export_dir=tmp_path / "exports")
    export.handle("export", "export")
    export.handle("export", "export")
    assert len(list((tmp_path / "exports").glob("astra_export_*.json"))) == 2


def test_export_leaves_no_temp_file(config, memory, tmp_path):
    export = ExportCommand(config, memory, export_dir=tmp_path / "exports")
    export.handle("export", "export")
    assert list((tmp_path / "exports").glob("*.tmp")) == []
