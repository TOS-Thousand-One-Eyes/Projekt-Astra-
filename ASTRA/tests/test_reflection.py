from actions.action_manager import ActionManager
from commands.reflection_command import ReflectionCommand
from commands.registry import build_default_registry
from experience.experience_manager import ExperienceManager
from experience.reflection_manager import ReflectionManager
from memory.memory_manager import MemoryManager


def test_reflection_manager_detects_echo_and_model_issues(tmp_path):
    experience = ExperienceManager(data_dir=tmp_path)
    experience.record_exchange("unknown intent", "I heard: unknown intent", command_name="echo")
    experience.record_exchange(
        "model check",
        "Local model unavailable: Ollama model is missing",
        command_name="ModelCommand",
    )
    reflections = ReflectionManager(data_dir=tmp_path)

    reflection = reflections.reflect(experience.recent())

    titles = [finding["title"] for finding in reflection["findings"]]
    assert reflection["id"] == "REF-0001"
    assert "Unrouted messages fell back to echo" in titles
    assert "Local model runtime needs attention" in titles


def test_reflection_manager_persists_reflections(tmp_path):
    reflections = ReflectionManager(data_dir=tmp_path)
    reflection = reflections.reflect([])

    reloaded = ReflectionManager(data_dir=tmp_path)

    assert reloaded.recent()[0]["id"] == reflection["id"]
    assert reloaded.stats()["total"] == 1


def test_reflection_command_formats_reflection(tmp_path):
    experience = ExperienceManager(data_dir=tmp_path)
    experience.record_exchange("unknown", "I heard: unknown", command_name="echo")
    command = ReflectionCommand(
        experience=experience,
        reflections=ReflectionManager(data_dir=tmp_path),
        actions=ActionManager(data_dir=tmp_path),
    )

    response = command.handle("reflect", "reflect")

    assert "Reflection REF-0001" in response
    assert "Unrouted messages fell back to echo" in response


def test_reflect_tasks_creates_action_items_from_findings(tmp_path):
    experience = ExperienceManager(data_dir=tmp_path)
    experience.record_exchange("anything", "Something went wrong handling that.", command_name="FailingCommand")
    actions = ActionManager(data_dir=tmp_path)
    command = ReflectionCommand(
        experience=experience,
        reflections=ReflectionManager(data_dir=tmp_path),
        actions=actions,
    )

    response = command.handle("reflect tasks", "reflect tasks")

    tasks = actions.list_tasks(status="all")
    assert "Created reflection tasks" in response
    assert len(tasks) == 1
    assert tasks[0]["priority"] == "high"
    assert tasks[0]["source"] == "reflection:REF-0001"


def test_default_registry_shares_reflections_with_jarvis_status(tmp_path, config):
    memory = MemoryManager(data_dir=tmp_path / "memory")
    experience = ExperienceManager(data_dir=tmp_path / "runtime")
    reflections = ReflectionManager(data_dir=tmp_path / "runtime")
    registry = build_default_registry(config, memory, experience=experience, reflections=reflections)

    experience.record_exchange("unknown", "I heard: unknown", command_name="echo")
    registry.dispatch("reflect")
    response = registry.dispatch("jarvis status").response

    assert "reflections: 1" in response
