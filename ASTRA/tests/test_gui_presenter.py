from gui.presenter import QUICK_COMMANDS, low_hw_summary, model_state_summary, runtime_title


class StubConfig:
    name = "Astra"
    version = "1.2.3"
    use_language_fallback = False
    language_model = "llama3.2:3b"


class StubClient:
    model = "gemma3:1b"


class StubLanguageModule:
    def __init__(self, available=False):
        self.available = available
        self.client = StubClient()


def test_model_state_summary_reports_ollama_off_without_module():
    summary = model_state_summary(StubConfig())

    assert summary["status"] == "Ollama off"
    assert summary["configured"] is False
    assert summary["available"] is False
    assert summary["model"] == "llama3.2:3b"
    assert "not used" in summary["detail"]


def test_model_state_summary_reports_restart_needed_when_configured_without_module():
    config = StubConfig()
    config.use_language_fallback = True

    summary = model_state_summary(config)

    assert summary["status"] == "Ollama on"
    assert summary["configured"] is True
    assert summary["available"] is False
    assert "runtime restart" in summary["detail"]


def test_model_state_summary_reports_available_session_model():
    config = StubConfig()
    config.use_language_fallback = True
    module = StubLanguageModule(available=True)

    summary = model_state_summary(config, module)

    assert summary["status"] == "Ollama ready"
    assert summary["available"] is True
    assert summary["model"] == "gemma3:1b"


def test_runtime_title_uses_name_and_version():
    assert runtime_title(StubConfig()) == "Astra v1.2.3"


def test_quick_commands_include_ollama_toggles_and_low_hw_model():
    commands = {command for _label, command in QUICK_COMMANDS}

    assert "ollama on" in commands
    assert "ollama off" in commands
    assert "model recommend-light" in commands


def test_low_hw_summary_states_no_extra_runtime_dependencies():
    assert "no browser engine" in low_hw_summary()
    assert "no extra runtime dependencies" in low_hw_summary()

