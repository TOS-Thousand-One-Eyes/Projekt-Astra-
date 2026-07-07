from actions.action_manager import ActionManager
from actions.system_action_manager import SystemActionManager
from automation.reminder_manager import ReminderManager
from commands.jarvis_command import JarvisCommand
from commands.registry import build_default_registry
from experience.experience_manager import ExperienceManager
from experience.reflection_manager import ReflectionManager
from learning.learning_manager import LearningManager
from memory.memory_manager import MemoryManager


class StubClient:
    model = "qwen3:4b"

    def __init__(self, failure=None):
        self.failure = failure
        self.checked = 0

    def ensure_available(self):
        self.checked += 1
        if self.failure:
            raise self.failure

    def generate_with_images(self, prompt, image_paths):
        return "image description"


class StubLanguageModule:

    def __init__(self, available=False, client=None):
        self.available = available
        self.client = client or StubClient()


class StubVisionClient:
    model = "llava:test"

    def __init__(self, failure=None):
        self.failure = failure
        self.checked = 0

    def ensure_available(self):
        self.checked += 1
        if self.failure:
            raise self.failure

    def generate_with_images(self, prompt, image_paths):
        return "image description"


class StubVisionDescriber:
    def __init__(self, client=None):
        self.client = client or StubVisionClient()

    def describe(self, image_path, prompt=None):
        return {"description": "image description", "path": image_path, "prompt": prompt}


class StubSpeech:
    def status(self):
        return {
            "platform": "test",
            "text_to_speech": True,
            "speech_to_text": True,
            "passive_listening": False,
        }


def build_command(tmp_path, language_module=None, speech=None, vision_describer=None):
    memory = MemoryManager(data_dir=tmp_path / "memory")
    learning = LearningManager(data_dir=tmp_path / "runtime")
    actions = ActionManager(data_dir=tmp_path / "runtime")
    system_actions = SystemActionManager(data_dir=tmp_path / "runtime")
    reminders = ReminderManager(data_dir=tmp_path / "runtime")
    experience = ExperienceManager(data_dir=tmp_path / "runtime")
    reflections = ReflectionManager(data_dir=tmp_path / "runtime")
    return JarvisCommand(
        memory,
        language_module=language_module,
        learning=learning,
        actions=actions,
        system_actions=system_actions,
        reminders=reminders,
        experience=experience,
        reflections=reflections,
        speech=speech or StubSpeech(),
        vision_describer=vision_describer,
    ), memory, learning


def test_jarvis_capabilities_reports_implemented_layers_and_known_gaps(tmp_path):
    command, memory, learning = build_command(tmp_path)
    memory.learn("operator", "Petr")
    memory.remember("Use source-backed learning before promotion.", entry_type="note")
    learning.learn(
        "Line balancing",
        target_level="proficient",
        source_candidates=[
            {
                "source": "memory:line-balancing",
                "content": "Line balancing uses takt time and separates evidence from advice.",
                "confidence": "high",
            }
        ],
    )

    response = command.handle("jarvis capabilities", "jarvis capabilities")

    assert response.startswith("JARVIS capability audit:")
    assert "Summary: ok=" in response
    assert "- [ok] Persistent memory: facts=1, long_memory_entries=1" in response
    assert "- [ok] Source-backed learning: subjects=1" in response
    assert "- [ok] Proficiency learning gate:" in response
    assert "- [partial] Local model runtime:" in response
    assert "- [ok] Image inspection:" in response
    assert "- [partial] Model-backed image description:" in response
    assert "- [ok] Bounded web research:" in response
    assert "- [ok] Speech-to-text input:" in response


def test_jarvis_audit_reports_available_local_model(tmp_path):
    command, _, _ = build_command(tmp_path, language_module=StubLanguageModule(available=True))

    response = command.handle("jarvis audit", "jarvis audit")

    assert "- [ok] Local model runtime: configured=true, available=true, model=qwen3:4b" in response


def test_default_registry_dispatches_jarvis_capability_audit(tmp_path, config):
    memory = MemoryManager(data_dir=tmp_path / "memory")
    learning = LearningManager(data_dir=tmp_path / "runtime")
    actions = ActionManager(data_dir=tmp_path / "runtime")
    system_actions = SystemActionManager(data_dir=tmp_path / "runtime")
    reminders = ReminderManager(data_dir=tmp_path / "runtime")
    experience = ExperienceManager(data_dir=tmp_path / "runtime")
    reflections = ReflectionManager(data_dir=tmp_path / "runtime")
    registry = build_default_registry(
        config,
        memory,
        learning=learning,
        actions=actions,
        system_actions=system_actions,
        reminders=reminders,
        experience=experience,
        reflections=reflections,
    )

    result = registry.dispatch("jarvis audit")

    assert result.command_name == "JarvisCommand"
    assert "JARVIS capability audit:" in result.response
    assert "- [ok] Transparent project log:" in result.response


def test_jarvis_verify_reports_runtime_warnings_without_model(tmp_path):
    command, _, _ = build_command(tmp_path)

    response = command.handle("jarvis verify", "jarvis verify")

    assert response.startswith("JARVIS runtime verification:")
    assert "- [pass] Persistent memory API:" in response
    assert "- [warn] Local model runtime: language module is not configured" in response
    assert "- [pass] Speech runtime: platform=test; tts=true; stt=true; passive_listening=false" in response


def test_jarvis_verify_marks_available_model_as_pass(tmp_path):
    module = StubLanguageModule(client=StubClient())
    command, _, _ = build_command(tmp_path, language_module=module)

    response = command.handle("jarvis self-check", "jarvis self-check")

    assert "- [pass] Local model runtime: available model=qwen3:4b" in response
    assert module.available is True
    assert module.client.checked == 1
    assert "- [warn] Model-backed image description:" in response


def test_jarvis_verify_checks_separate_vision_model_client(tmp_path):
    vision_client = StubVisionClient()
    command, _, _ = build_command(tmp_path, vision_describer=StubVisionDescriber(client=vision_client))

    response = command.handle("jarvis verify", "jarvis verify")

    assert "- [warn] Model-backed image description: vision model runtime is available model=llava:test" in response
    assert vision_client.checked == 1


def test_default_registry_dispatches_jarvis_verify(tmp_path, config):
    memory = MemoryManager(data_dir=tmp_path / "memory")
    registry = build_default_registry(config, memory, speech=StubSpeech())

    result = registry.dispatch("jarvis verify")

    assert result.command_name == "JarvisCommand"
    assert "JARVIS runtime verification:" in result.response
    assert "- [pass] Speech runtime: platform=test" in result.response


def test_default_registry_does_not_report_language_fallback_as_dedicated_vision_model(tmp_path, config):
    memory = MemoryManager(data_dir=tmp_path / "memory")
    module = StubLanguageModule(available=True)
    registry = build_default_registry(config, memory, language_module=module, speech=StubSpeech())

    status = registry.dispatch("jarvis status").response
    verify = registry.dispatch("jarvis verify").response

    assert "- local vision model configured: false" in status
    assert "configured vision model" not in verify
    assert "through language model=qwen3:4b" in verify
