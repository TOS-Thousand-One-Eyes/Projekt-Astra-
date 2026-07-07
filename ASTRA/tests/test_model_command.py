import json

from commands.model_command import ModelCommand
from commands.registry import build_default_registry
from config.config import Config
from memory.memory_manager import MemoryManager


class StubClient:
    model = "qwen3:4b"
    base_url = "http://localhost:11434"

    def __init__(self, response="ASTRA-OK", failure=None):
        self.response = response
        self.failure = failure
        self.checked = 0
        self.prompts = []

    def ensure_available(self):
        self.checked += 1
        if self.failure:
            raise self.failure

    def list_models(self):
        if self.failure:
            raise self.failure
        return [
            {
                "name": "llama3.2:3b",
                "parameter_size": "3.2B",
                "capabilities": ["completion", "tools"],
            },
            {
                "name": "qwen3:4b",
                "parameter_size": "4B",
                "capabilities": ["completion"],
            },
        ]

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self.response


class StubLanguageModule:

    def __init__(self, client):
        self.client = client
        self.available = False

    def respond(self, message):
        if not self.available:
            return None
        return self.client.generate(message)


def test_model_status_reports_unconfigured_module():
    command = ModelCommand()

    response = command.handle("model status", "model status")

    assert "configured: false" in response


def test_model_check_marks_language_module_available():
    client = StubClient()
    module = StubLanguageModule(client)
    command = ModelCommand(language_module=module)

    response = command.handle("model check", "model check")

    assert "Local model available" in response
    assert "qwen3:4b" in response
    assert module.available is True
    assert client.checked == 1


def test_model_check_reports_unavailable_model():
    client = StubClient(failure=ValueError("model is missing"))
    module = StubLanguageModule(client)
    module.available = True
    command = ModelCommand(language_module=module)

    response = command.handle("model check", "model check")

    assert "Local model unavailable: model is missing" in response
    assert module.available is False


def test_model_list_reports_installed_ollama_models():
    client = StubClient()
    module = StubLanguageModule(client)
    command = ModelCommand(language_module=module)

    response = command.handle("model list", "model list")

    assert response.startswith("Installed Ollama models:")
    assert "- qwen3:4b [current] (4B; capabilities=completion)" in response
    assert "- llama3.2:3b (3.2B; capabilities=completion,tools)" in response


def test_model_use_switches_runtime_client_and_persists_config(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "version": "1.2.3",
                "use_language_fallback": True,
                "language_model": "qwen3:4b",
            }
        ),
        encoding="utf-8",
    )
    config = Config(path=config_path)
    client = StubClient()
    module = StubLanguageModule(client)
    module.available = True
    command = ModelCommand(language_module=module, config=config)

    response = command.handle("model use llama3.2:3b", "model use llama3.2:3b")

    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert response == "Configured local model: llama3.2:3b. Persisted to config.json. Run `model check` or `model smoke`."
    assert client.model == "llama3.2:3b"
    assert module.available is False
    assert config.language_model == "llama3.2:3b"
    assert saved["language_model"] == "llama3.2:3b"
    assert saved["use_language_fallback"] is True


def test_model_use_rejects_uninstalled_model_without_changing_runtime():
    client = StubClient()
    module = StubLanguageModule(client)
    command = ModelCommand(language_module=module)

    response = command.handle("model use missing:model", "model use missing:model")

    assert "Model 'missing:model' is not installed" in response
    assert "llama3.2:3b" in response
    assert client.model == "qwen3:4b"


def test_model_ask_verifies_runtime_then_returns_response():
    client = StubClient(response="Hello from the local model")
    module = StubLanguageModule(client)
    command = ModelCommand(language_module=module)

    response = command.handle("model ask Say hello", "model ask say hello")

    assert response == "Model response:\nHello from the local model"
    assert client.checked == 1
    assert client.prompts == ["Say hello"]


def test_model_smoke_uses_fixed_smoke_prompt():
    client = StubClient(response="ASTRA-OK")
    module = StubLanguageModule(client)
    command = ModelCommand(language_module=module)

    response = command.handle("model smoke", "model smoke")

    assert response == "Model response:\nASTRA-OK"
    assert client.prompts == [ModelCommand.SMOKE_PROMPT]


def test_default_registry_shares_model_state_with_jarvis_status(tmp_path, config):
    memory = MemoryManager(data_dir=tmp_path / "memory")
    module = StubLanguageModule(StubClient())
    registry = build_default_registry(config, memory, language_module=module)

    registry.dispatch("model check")
    response = registry.dispatch("jarvis status").response

    assert "local model configured: true" in response
    assert "local model available: true" in response
    assert "local model: qwen3:4b" in response
