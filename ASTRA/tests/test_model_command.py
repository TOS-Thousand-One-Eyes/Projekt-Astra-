import json

from commands.model_command import ModelCommand
from config.config import Config


class StubClient:
    def __init__(self, response="ASTRA-OK", failure=None):
        self.model = "qwen3:4b"
        self.base_url = "http://localhost:11434"
        self.response = response
        self.failure = failure
        self.checked = 0
        self.prompts = []
        self.busy = False

    def ensure_available(self):
        self.checked += 1
        if self.failure:
            raise self.failure

    def list_models(self):
        if self.failure:
            raise self.failure
        return [
            {"name": "gemma3:4b", "parameter_size": "4.3B", "capabilities": ["completion", "vision"]},
            {"name": "qwen3:4b", "parameter_size": "4B", "capabilities": ["completion"]},
        ]

    def capabilities(self, model=None):
        if (model or self.model) == "gemma3:4b":
            return ["completion", "vision"]
        return ["completion"]

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self.response


class StubLanguageModule:
    def __init__(self, client):
        self.client = client
        self.available = False
        self.stopped = False

    def stop(self):
        self.available = False
        self.stopped = True

    def respond(self, message):
        if not self.available:
            return None
        return self.client.generate(message)


class ObserverStub:
    def __init__(self, client, enabled=True):
        self.describer = type("Describer", (), {"client": client})()
        self.enabled = enabled
        self.disabled = False

    def disable(self):
        self.enabled = False
        self.disabled = True


def make_config(tmp_path, enabled=True, model="qwen3:4b"):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "version": "1.2.3",
                "use_language_fallback": enabled,
                "language_model": model,
            }
        ),
        encoding="utf-8",
    )
    return Config(path=path), path


def test_model_status_reports_unconfigured_module():
    assert "configured: false" in ModelCommand().handle("model status", "model status")


def test_model_check_marks_language_module_available():
    client = StubClient()
    module = StubLanguageModule(client)
    response = ModelCommand(language_module=module).handle("model check", "model check")
    assert "Model available" in response
    assert "qwen3:4b" in response
    assert module.available is True
    assert client.checked == 1


def test_model_check_reports_unavailable_model():
    client = StubClient(failure=ValueError("model is missing"))
    module = StubLanguageModule(client)
    module.available = True
    response = ModelCommand(language_module=module).handle("model check", "model check")
    assert "Model unavailable: model is missing" in response
    assert module.available is False


def test_model_list_reports_registered_models_and_current_marker():
    client = StubClient()
    module = StubLanguageModule(client)
    response = ModelCommand(language_module=module).handle("model list", "model list")
    assert response.startswith("Installed/registered Ollama models:")
    assert "qwen3:4b [current]" in response
    assert "gemma3:4b" in response


def test_model_use_switches_immediately_and_persists(tmp_path):
    config, path = make_config(tmp_path)
    client = StubClient()
    module = StubLanguageModule(client)
    module.available = True
    response = ModelCommand(module, config).handle("model use gemma3:4b", "model use gemma3:4b")
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert "Model switched and ready: gemma3:4b" in response
    assert client.model == "gemma3:4b"
    assert module.available is True
    assert config.language_model == "gemma3:4b"
    assert saved["language_model"] == "gemma3:4b"
    assert saved["use_language_fallback"] is True


def test_failed_model_switch_rolls_back_and_does_not_persist(tmp_path):
    config, path = make_config(tmp_path)
    client = StubClient()
    module = StubLanguageModule(client)
    module.available = True

    original_ensure = client.ensure_available

    def fail_new():
        if client.model == "gemma3:4b":
            raise ValueError("cannot load")
        return original_ensure()

    client.ensure_available = fail_new
    response = ModelCommand(module, config).handle("model use gemma3:4b", "model use gemma3:4b")
    assert "kept qwen3:4b" in response
    assert client.model == "qwen3:4b"
    assert module.available is True
    assert json.loads(path.read_text(encoding="utf-8"))["language_model"] == "qwen3:4b"


def test_model_use_rejects_unregistered_model():
    client = StubClient()
    module = StubLanguageModule(client)
    response = ModelCommand(module).handle("model use missing:model", "model use missing:model")
    assert "not installed/registered" in response
    assert client.model == "qwen3:4b"


def test_switching_shared_eyes_to_text_only_model_disables_eyes(tmp_path):
    config, path = make_config(tmp_path, model="gemma3:4b")
    client = StubClient()
    client.model = "gemma3:4b"
    module = StubLanguageModule(client)
    module.available = True
    observer = ObserverStub(client, enabled=True)
    response = ModelCommand(module, config, screen_observer=observer).handle(
        "model use qwen3:4b", "model use qwen3:4b"
    )
    assert observer.disabled is True
    assert "Eyes were disabled" in response
    assert json.loads(path.read_text(encoding="utf-8"))["screen_observer_enabled"] is False


def test_switching_to_vision_model_keeps_shared_eyes_available(tmp_path):
    config, _path = make_config(tmp_path)
    client = StubClient()
    module = StubLanguageModule(client)
    module.available = True
    observer = ObserverStub(client, enabled=True)
    response = ModelCommand(module, config, screen_observer=observer).handle(
        "model use gemma3:4b", "model use gemma3:4b"
    )
    assert observer.enabled is True
    assert "Eyes were disabled" not in response


def test_model_disable_persists_and_stops_session(tmp_path):
    config, path = make_config(tmp_path, enabled=True)
    module = StubLanguageModule(StubClient())
    module.available = True
    response = ModelCommand(module, config).handle("ollama off", "ollama off")
    assert response.startswith("Ollama fallback disabled.")
    assert module.stopped is True
    assert config.use_language_fallback is False
    assert json.loads(path.read_text(encoding="utf-8"))["use_language_fallback"] is False


def test_model_enable_without_session_module_requests_restart(tmp_path):
    config, path = make_config(tmp_path, enabled=False)
    response = ModelCommand(config=config).handle("ollama enable", "ollama enable")
    assert "Restart ASTRA" in response
    assert config.use_language_fallback is True
    assert json.loads(path.read_text(encoding="utf-8"))["use_language_fallback"] is True


def test_model_recommendations_keep_offline_options():
    command = ModelCommand()
    balanced = command.handle("model recommend", "model recommend")
    light = command.handle("model recommend-light", "model recommend-light")
    assert "gemma3:4b" in balanced
    assert "ollama pull gemma3:4b" in balanced
    assert "gemma3:1b" in light
    assert "ollama pull gemma3:1b" in light


def test_model_ask_checks_runtime_and_returns_response():
    client = StubClient(response="Hello")
    module = StubLanguageModule(client)
    response = ModelCommand(module).handle("model ask Say hello", "model ask say hello")
    assert response == "Model response:\nHello"
    assert client.checked == 1
    assert client.prompts == ["Say hello"]


def test_model_smoke_uses_fixed_prompt():
    client = StubClient(response="ASTRA-OK")
    module = StubLanguageModule(client)
    response = ModelCommand(module).handle("model smoke", "model smoke")
    assert response == "Model response:\nASTRA-OK"
    assert client.prompts == [ModelCommand.SMOKE_PROMPT]
