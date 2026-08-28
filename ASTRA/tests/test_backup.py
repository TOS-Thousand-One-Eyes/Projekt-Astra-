import json
import zipfile
from types import SimpleNamespace

from commands.backup_command import (
    BACKUP_SCHEMA,
    BackupCommand,
    safe_archive_name,
)
from memory.memory_manager import MemoryManager


def populated_command(tmp_path, config, user_id="erik"):
    profile_dir = tmp_path / "users" / user_id
    memory = MemoryManager(data_dir=profile_dir)
    memory.learn("name", user_id.title())
    memory.remember("Keep this personal note.", entry_type="note")
    learning_file = profile_dir / "learning" / "hydraulics.json"
    learning_file.parent.mkdir(parents=True)
    learning_file.write_text(
        json.dumps({"subject": "Hydraulics", "sources": []}),
        encoding="utf-8",
    )
    guidance_file = profile_dir / "self_learning" / "guidance.json"
    guidance_file.parent.mkdir(parents=True)
    guidance_file.write_text("[]", encoding="utf-8")
    identity = SimpleNamespace(
        user_id=user_id,
        display_name=user_id.title(),
        data_dir=profile_dir,
    )
    return BackupCommand(config, memory, identity=identity), profile_dir


def test_backup_create_writes_verified_profile_zip(tmp_path, config):
    command, profile_dir = populated_command(tmp_path, config)

    created = command.create("before update")
    verification = command.verify(created["path"].name)

    assert created["path"].parent == profile_dir / "backups"
    assert "before-update" in created["path"].name
    assert verification["valid"] is True
    assert verification["files"] == 4
    assert len(created["sha256"]) == 64
    assert list((profile_dir / "backups").glob("*.tmp")) == []

    with zipfile.ZipFile(created["path"], "r") as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["schema"] == BACKUP_SCHEMA
        assert manifest["user_id"] == "erik"
        assert manifest["file_count"] == 4
        assert "backups" not in {name.split("/", 1)[0] for name in archive.namelist()}


def test_backup_commands_create_list_and_verify_latest(tmp_path, config):
    command, _profile_dir = populated_command(tmp_path, config)

    created = command.handle("backup create before update", "backup create before update")
    listed = command.handle("backup list", "backup list")
    verified = command.handle("backup verify latest", "backup verify latest")

    assert "Verified profile backup created" in created
    assert "Keep this ZIP private" in created
    assert "astra_backup_erik" in listed
    assert "Backup verified" in verified


def test_backup_detects_manifest_hash_mismatch(tmp_path, config):
    command, _profile_dir = populated_command(tmp_path, config)
    command.backup_dir.mkdir(parents=True, exist_ok=True)
    path = command.backup_dir / "astra_backup_erik_broken.zip"
    content = b"real content"
    manifest = {
        "schema": BACKUP_SCHEMA,
        "file_count": 1,
        "total_bytes": len(content),
        "files": [
            {
                "path": "facts.json",
                "size": len(content),
                "sha256": "0" * 64,
            }
        ],
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("facts.json", content)
        archive.writestr("manifest.json", json.dumps(manifest))

    report = command.verify(path.name)

    assert report["valid"] is False
    assert "SHA-256 mismatch: facts.json" in report["issues"]


def test_profile_backups_are_isolated_between_erik_and_petr(tmp_path, config):
    erik, erik_dir = populated_command(tmp_path, config, user_id="erik")
    petr, petr_dir = populated_command(tmp_path, config, user_id="petr")

    erik_backup = erik.create()["path"]
    petr_backup = petr.create()["path"]

    assert erik_backup.parent == erik_dir / "backups"
    assert petr_backup.parent == petr_dir / "backups"
    assert erik_backup.parent != petr_backup.parent
    assert erik.list_backups()[0]["name"] == erik_backup.name
    assert petr.list_backups()[0]["name"] == petr_backup.name


def test_backup_refuses_paths_and_unsafe_archive_names(tmp_path, config):
    command, _profile_dir = populated_command(tmp_path, config)

    response = command.handle(
        "backup verify ../other.zip",
        "backup verify ../other.zip",
    )

    assert "accepts a filename, not a path" in response
    assert safe_archive_name("learning/topic.json") is True
    assert safe_archive_name("../facts.json") is False
    assert safe_archive_name("C:\\facts.json") is False


def test_backup_reports_when_profile_has_no_persistent_data(tmp_path, config):
    profile_dir = tmp_path / "users" / "erik"
    memory = MemoryManager(data_dir=profile_dir)
    command = BackupCommand(config, memory, profile_dir=profile_dir)

    response = command.handle("backup create", "backup create")

    assert "No persistent profile data exists yet" in response
