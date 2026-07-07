from commands.experience_command import ExperienceCommand
from commands.registry import build_default_registry
from core.brain import Brain
from experience.experience_manager import ExperienceManager
from memory.memory_manager import MemoryManager
from modules.modules import Modules
from utils.logger import Logger


def test_experience_manager_records_and_persists_exchange(tmp_path):
    experience = ExperienceManager(data_dir=tmp_path)

    exchange = experience.record_exchange(
        "hi",
        "Hello!",
        command_name="GreetingCommand",
        session_id="SESSION-TEST",
    )

    assert exchange["id"] == "EXP-0001"
    assert exchange["command"] == "GreetingCommand"
    assert exchange["session_id"] == "SESSION-TEST"

    reloaded = ExperienceManager(data_dir=tmp_path)
    assert reloaded.recent()[0]["user"] == "hi"
    assert reloaded.recent()[0]["assistant"] == "Hello!"


def test_experience_manager_search_and_stats(tmp_path):
    experience = ExperienceManager(data_dir=tmp_path)
    experience.record_exchange("remember compressor oil", "Got it", command_name="MemoryCommand")
    experience.record_exchange("hi", "Hello!", command_name="GreetingCommand")

    matches = experience.search("compressor")
    stats = experience.stats()

    assert len(matches) == 1
    assert matches[0]["command"] == "MemoryCommand"
    assert stats["total"] == 2
    assert stats["commands"] == {"MemoryCommand": 1, "GreetingCommand": 1}


def test_experience_command_reports_recent_search_and_stats(tmp_path):
    experience = ExperienceManager(data_dir=tmp_path)
    experience.record_exchange("hi", "Hello!", command_name="GreetingCommand")
    command = ExperienceCommand(experience=experience)

    recent = command.handle("experience recent", "experience recent")
    search = command.handle("experience search hello", "experience search hello")
    stats = command.handle("experience stats", "experience stats")

    assert "EXP-0001" in recent
    assert "GreetingCommand" in search
    assert "total exchanges: 1" in stats


def test_brain_records_structured_experience_for_receive(tmp_path, config):
    memory = MemoryManager(data_dir=tmp_path / "memory")
    experience = ExperienceManager(data_dir=tmp_path / "runtime")
    brain = Brain(Logger(), config, memory, Modules(Logger()), experience=experience)

    brain.start()
    response = brain.receive("hi")

    exchanges = experience.recent()
    assert response == "Hello!"
    assert len(exchanges) == 1
    assert exchanges[0]["user"] == "hi"
    assert exchanges[0]["assistant"] == "Hello!"
    assert exchanges[0]["command"] == "GreetingCommand"
    assert exchanges[0]["session_id"].startswith("SESSION-")


def test_default_registry_shares_experience_with_jarvis_status(tmp_path, config):
    memory = MemoryManager(data_dir=tmp_path / "memory")
    experience = ExperienceManager(data_dir=tmp_path / "runtime")
    registry = build_default_registry(config, memory, experience=experience)

    experience.record_exchange("hi", "Hello!", command_name="GreetingCommand")
    response = registry.dispatch("jarvis status").response

    assert "structured experiences: 1" in response
