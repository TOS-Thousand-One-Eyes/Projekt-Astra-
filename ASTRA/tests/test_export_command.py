import json

from commands.export_command import ExportCommand


def test_export_creates_file_with_expected_keys_and_values(config, memory, tmp_path):
    memory.learn("name", "Erik")
    memory.remember("buy milk")

    export = ExportCommand(config, memory, export_dir=tmp_path / "exports")
    export.handle("export", "export")

    files = list((tmp_path / "exports").glob("astra_export_*.json"))
    assert len(files) == 1

    with open(files[0], "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "exported_at" in data
    assert data["config"] == {
        "name": config.name,
        "version": config.version,
        "log_level": config.log_level,
        "log_to_file": config.log_to_file,
        "check_for_updates": config.check_for_updates,
        "use_language_fallback": config.use_language_fallback,
        "language_base_url": config.language_base_url,
        "language_model": config.language_model,
        "language_generate_timeout": config.language_generate_timeout,
        "use_vision_model": config.use_vision_model,
        "vision_base_url": config.vision_base_url,
        "vision_model": config.vision_model,
        "vision_generate_timeout": config.vision_generate_timeout,
    }
    assert data["facts"] == {"name": "Erik"}
    assert data["long_memory"][0]["entry"] == "buy milk"


def test_export_response_mentions_exported_file(config, memory, tmp_path):
    export_dir = tmp_path / "exports"
    export = ExportCommand(config, memory, export_dir=export_dir)
    response = export.handle("export", "export")

    assert "Exported" in response
    assert str(export_dir) in response


def test_export_ignores_unrelated_messages(config, memory, tmp_path):
    export = ExportCommand(config, memory, export_dir=tmp_path / "exports")
    assert export.handle("hello", "hello") is None
    assert not (tmp_path / "exports").exists()


def test_two_exports_in_the_same_second_do_not_overwrite_each_other(config, memory, tmp_path):
    export = ExportCommand(config, memory, export_dir=tmp_path / "exports")
    export.handle("export", "export")
    export.handle("export", "export")

    files = list((tmp_path / "exports").glob("astra_export_*.json"))
    assert len(files) == 2


def test_export_leaves_no_leftover_temp_file(config, memory, tmp_path):
    export = ExportCommand(config, memory, export_dir=tmp_path / "exports")
    export.handle("export", "export")

    tmp_files = list((tmp_path / "exports").glob("*.tmp"))
    assert tmp_files == []
