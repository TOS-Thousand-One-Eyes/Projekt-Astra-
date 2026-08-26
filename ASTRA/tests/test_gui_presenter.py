from gui.presenter import (
    QUICK_COMMANDS,
    low_hw_summary,
    model_state_summary,
    normalize_theme,
    runtime_title,
    theme_button_label,
)


class StubConfig:
    name = "Astra"
    version = "1.2.3"
    use_language_fallback = False
    language_model = "llama3.2:3b"


class StubClient:
    model = "gemma3:1b"
    busy = False


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


def test_model_state_summary_reports_available_session_model_and_busy_state():
    config = StubConfig()
    config.use_language_fallback = True
    module = StubLanguageModule(available=True)
    summary = model_state_summary(config, module)
    assert summary["status"] == "Ollama ready"
    assert summary["available"] is True
    assert summary["model"] == "gemma3:1b"
    assert summary["busy"] is False


def test_runtime_title_uses_name_and_version():
    assert runtime_title(StubConfig()) == "Astra v1.2.3"


def test_quick_commands_preserve_existing_actions_and_add_new_statuses():
    commands = {command for _label, command in QUICK_COMMANDS}
    for command in (
        "ollama on",
        "ollama off",
        "model recommend-light",
        "eyes status",
        "self learning status",
        "help",
    ):
        assert command in commands


def test_theme_helpers():
    assert normalize_theme("LIGHT") == "light"
    assert normalize_theme("invalid") == "dark"
    assert theme_button_label("dark") == "Light mode"
    assert theme_button_label("light") == "Dark mode"


def test_low_hw_summary_is_truthful_about_new_dependencies():
    summary = low_hw_summary()
    assert "no browser engine" in summary
    assert "4K" in summary
    assert "mss/Pillow/psutil" in summary
