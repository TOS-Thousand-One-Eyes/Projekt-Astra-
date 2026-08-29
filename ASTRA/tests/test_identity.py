import json
from contextlib import contextmanager

import pytest

from commands.identity_command import IdentityCommand
from config.config import Config
from core.brain import Brain
from experience.experience_manager import ExperienceManager
from gui.app import build_brain
from identity.identity_manager import (
    AuthenticationError,
    IdentityManager,
    IdentityStoreError,
)
from memory.context_builder import build_model_prompt
from memory.memory_manager import MemoryManager
from modules.modules import Modules
from main import prompt_cli_identity
from utils.logger import Logger


def configured_manager(tmp_path):
    manager = IdentityManager(data_dir=tmp_path)
    manager.initialize_pin("erik", "1234")
    manager.initialize_pin("petr", "5678")
    return manager


def test_default_profiles_are_erik_and_petr(tmp_path):
    profiles = IdentityManager(data_dir=tmp_path).list_profiles()
    assert [(item["id"], item["display_name"]) for item in profiles] == [
        ("erik", "Erik"),
        ("petr", "Petr"),
    ]
    assert all(item["pin_configured"] is False for item in profiles)


def test_cli_first_login_creates_pin_and_opens_selected_profile(tmp_path):
    manager = IdentityManager(data_dir=tmp_path)
    answers = iter(["Petr"])
    pins = iter(["5678", "5678"])

    identity = prompt_cli_identity(
        manager,
        input_func=lambda _prompt: next(answers),
        pin_reader=lambda _prompt: next(pins),
    )

    assert identity.user_id == "petr"
    assert manager.authenticate("petr", "5678").display_name == "Petr"


def test_cli_login_retries_after_wrong_pin(tmp_path):
    manager = configured_manager(tmp_path)
    answers = iter(["Erik", "Erik"])
    pins = iter(["0000", "1234"])

    identity = prompt_cli_identity(
        manager,
        input_func=lambda _prompt: next(answers),
        pin_reader=lambda _prompt: next(pins),
    )

    assert identity.user_id == "erik"


def test_pin_authentication_opens_isolated_profile_directory(tmp_path):
    manager = configured_manager(tmp_path)
    erik = manager.authenticate("Erik", "1234")
    petr = manager.authenticate("petr", "5678")

    assert erik.user_id == "erik"
    assert erik.display_name == "Erik"
    assert erik.data_dir == tmp_path / "users" / "erik"
    assert petr.data_dir == tmp_path / "users" / "petr"
    assert erik.data_dir != petr.data_dir


def test_pin_persists_across_identity_manager_recreation(tmp_path):
    manager = IdentityManager(data_dir=tmp_path)
    manager.initialize_pin("petr", "5678")

    reloaded = IdentityManager(data_dir=tmp_path)

    assert reloaded.resolve_profile("petr")["pin_configured"] is True
    assert reloaded.authenticate("petr", "5678").display_name == "Petr"
    with pytest.raises(IdentityStoreError, match="already configured"):
        reloaded.initialize_pin("petr", "9999")


def test_two_manager_instances_do_not_overwrite_each_others_pin_changes(tmp_path):
    first = IdentityManager(data_dir=tmp_path)
    second = IdentityManager(data_dir=tmp_path)

    first.initialize_pin("erik", "1234")
    second.initialize_pin("petr", "5678")

    reloaded = IdentityManager(data_dir=tmp_path)
    assert reloaded.authenticate("erik", "1234").user_id == "erik"
    assert reloaded.authenticate("petr", "5678").user_id == "petr"


def test_last_seen_version_is_profile_linked_and_does_not_change_pin(tmp_path):
    manager = configured_manager(tmp_path)
    before = json.loads(manager.path.read_text(encoding="utf-8"))
    erik_pin = before["profiles"][0]["pin"]

    assert manager.mark_version_seen(
        "erik",
        "0.0.19",
        seen_at="2026-08-28T12:00:00",
    ) is True
    assert manager.mark_version_seen(
        "petr",
        "0.0.22",
        seen_at="2026-08-28T12:05:00",
    ) is True

    reloaded = IdentityManager(data_dir=tmp_path)
    assert reloaded.authenticate("erik", "1234").last_seen_version == "0.0.19"
    assert reloaded.authenticate("petr", "5678").last_seen_version == "0.0.22"
    after = json.loads(reloaded.path.read_text(encoding="utf-8"))
    assert after["profiles"][0]["pin"] == erik_pin


def test_older_checkout_cannot_downgrade_profile_last_seen_version(tmp_path):
    manager = configured_manager(tmp_path)
    manager.mark_version_seen("erik", "0.0.22")

    assert manager.mark_version_seen("erik", "0.0.21") is False
    assert manager.authenticate("erik", "1234").last_seen_version == "0.0.22"


def test_invalid_last_seen_timestamp_cannot_corrupt_profile_store(tmp_path):
    manager = configured_manager(tmp_path)

    with pytest.raises(ValueError, match="ISO 8601"):
        manager.mark_version_seen("erik", "0.0.22", seen_at=12345)

    reloaded = IdentityManager(data_dir=tmp_path)
    assert reloaded.authenticate("erik", "1234").last_seen_version is None


def test_legacy_checkout_pin_and_profile_data_migrate_to_stable_root(tmp_path):
    legacy_root = tmp_path / "checkout" / "data"
    stable_root = tmp_path / "appdata" / "ASTRA"
    legacy = IdentityManager(data_dir=legacy_root)
    legacy.initialize_pin("petr", "5678")
    old_note = legacy_root / "users" / "petr" / "long_memory.json"
    old_note.parent.mkdir(parents=True, exist_ok=True)
    old_note.write_text('[{"content":"keep me"}]', encoding="utf-8")

    migrated = IdentityManager(
        data_dir=stable_root,
        legacy_data_dir=legacy_root,
    )
    identity = migrated.authenticate("petr", "5678")

    assert identity.data_dir == stable_root / "users" / "petr"
    assert (identity.data_dir / "long_memory.json").read_text(encoding="utf-8") == (
        '[{"content":"keep me"}]'
    )
    assert old_note.exists()


def test_wrong_pin_is_rejected(tmp_path):
    manager = configured_manager(tmp_path)
    with pytest.raises(AuthenticationError, match="Incorrect PIN"):
        manager.authenticate("erik", "9999")


def test_changing_pin_invalidates_the_previous_pin(tmp_path):
    manager = configured_manager(tmp_path)
    manager.change_pin("erik", "1234", "4321")

    with pytest.raises(AuthenticationError):
        manager.authenticate("erik", "1234")
    assert manager.authenticate("erik", "4321").display_name == "Erik"


def test_change_pin_rechecks_current_pin_inside_mutation_transaction(tmp_path):
    first = configured_manager(tmp_path)
    second = IdentityManager(data_dir=tmp_path)

    @contextmanager
    def interleaved_file_lock():
        second.change_pin("erik", "1234", "2222")
        yield

    first._file_lock = interleaved_file_lock

    with pytest.raises(AuthenticationError, match="Incorrect PIN"):
        first.change_pin("erik", "1234", "1111")

    assert IdentityManager(data_dir=tmp_path).authenticate("erik", "2222")


def test_last_seen_version_rejects_non_numeric_value_without_rollback(tmp_path):
    manager = configured_manager(tmp_path)
    manager.mark_version_seen("petr", "2.0")

    with pytest.raises(ValueError, match="dotted version"):
        manager.mark_version_seen("petr", "banana")

    assert manager.authenticate("petr", "5678").last_seen_version == "2.0"


def test_pin_is_salted_and_hashed_not_stored_as_plaintext(tmp_path):
    manager = IdentityManager(data_dir=tmp_path)
    manager.initialize_pin("erik", "2468")
    payload = json.loads(manager.path.read_text(encoding="utf-8"))
    record = payload["profiles"][0]["pin"]

    assert record["algorithm"] == "pbkdf2_sha256"
    assert record["iterations"] >= 100_000
    assert record["hash"] != "2468"
    assert record["salt"] != "2468"


def test_pin_must_be_four_to_twelve_digits(tmp_path):
    manager = IdentityManager(data_dir=tmp_path)
    for value in ("123", "abcd", "1234567890123"):
        with pytest.raises(ValueError, match="4 to 12 digits"):
            manager.initialize_pin("erik", value)


def test_corrupt_identity_store_fails_closed_without_reset(tmp_path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir(parents=True)
    path = identity_dir / "profiles.json"
    path.write_text("{broken", encoding="utf-8")

    with pytest.raises(IdentityStoreError):
        IdentityManager(data_dir=tmp_path)
    assert path.read_text(encoding="utf-8") == "{broken"


def test_identity_store_rejects_excessive_pin_work_factor(tmp_path):
    manager = IdentityManager(data_dir=tmp_path)
    manager.initialize_pin("erik", "2468")
    payload = json.loads(manager.path.read_text(encoding="utf-8"))
    payload["profiles"][0]["pin"]["iterations"] = 1_000_000_000
    manager.path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(IdentityStoreError, match="PIN record"):
        IdentityManager(data_dir=tmp_path)


def test_legacy_runtime_data_is_copied_to_erik_and_original_is_retained(tmp_path):
    (tmp_path / "long_memory.json").write_text('[{"entry":"legacy"}]', encoding="utf-8")
    old_guidance = tmp_path / "self_learning" / "guidance.json"
    old_guidance.parent.mkdir(parents=True)
    old_guidance.write_text("[]", encoding="utf-8")

    manager = IdentityManager(data_dir=tmp_path)
    manager.initialize_pin("erik", "1234")
    session = manager.session_after_setup("erik")

    assert (session.data_dir / "long_memory.json").exists()
    assert (session.data_dir / "self_learning" / "guidance.json").exists()
    assert (tmp_path / "long_memory.json").exists()
    assert old_guidance.exists()
    assert manager.migrate_legacy_data("erik") == []


def test_legacy_data_is_not_assigned_to_petr(tmp_path):
    (tmp_path / "facts.json").write_text('{"name":"Erik"}', encoding="utf-8")
    manager = IdentityManager(data_dir=tmp_path)
    manager.initialize_pin("petr", "5678")
    session = manager.session_after_setup("petr")
    assert not (session.data_dir / "facts.json").exists()


def test_identity_command_reports_active_profile_without_accepting_chat_pin(tmp_path):
    manager = configured_manager(tmp_path)
    identity = manager.authenticate("erik", "1234")
    command = IdentityCommand(identity=identity, identity_manager=manager)

    status = command.handle("who am i", "who am i")
    switch = command.handle("user switch petr", "user switch petr")

    assert "Erik" in status and "erik" in status
    assert "never accepted through chat" in status
    assert "Lock / switch" in switch


def test_model_prompt_names_only_the_active_profile(tmp_path):
    manager = configured_manager(tmp_path)
    identity = manager.authenticate("erik", "1234")
    memory = MemoryManager(data_dir=identity.data_dir)

    prompt = build_model_prompt("hello", memory, identity=identity)

    assert "Active local user: Erik (user_id=erik)" in prompt
    assert "Petr" not in prompt


def test_gui_runtime_factory_wires_personal_stores_to_active_profile(tmp_path):
    manager = configured_manager(tmp_path / "runtime-data")
    erik = manager.authenticate("erik", "1234")
    petr = manager.authenticate("petr", "5678")
    config = Config(path=tmp_path / "config.json")

    erik_brain = build_brain(config, Logger(), erik, manager)
    petr_brain = build_brain(config, Logger(), petr, manager)
    erik_brain.memory.learn("favorite color", "blue")

    assert petr_brain.memory.get_fact("favorite color") is None
    assert erik_brain.process("hi") == "Hello, Erik!"
    assert petr_brain.process("hi") == "Hello, Petr!"
    for component in (
        erik_brain.memory.long_memory.path,
        erik_brain.learning.root,
        erik_brain.self_learning.root,
        erik_brain.experience.root,
    ):
        assert erik.data_dir == component or erik.data_dir in component.parents


def test_brain_tags_structured_experience_with_active_actor_id(tmp_path):
    manager = configured_manager(tmp_path / "runtime-data")
    identity = manager.authenticate("erik", "1234")
    memory = MemoryManager(data_dir=identity.data_dir)
    experience = ExperienceManager(data_dir=identity.data_dir)
    config = Config(path=tmp_path / "config.json")
    brain = Brain(
        Logger(),
        config,
        memory,
        Modules(Logger()),
        experience=experience,
        identity=identity,
    )

    brain.start()
    brain.receive("hi")

    assert experience.recent()[0]["actor_id"] == "erik"
