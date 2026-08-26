GUI_THEMES = {
    "dark": {
        "root": "#0d1117",
        "panel": "#161b22",
        "border": "#30363d",
        "text": "#e6edf3",
        "subtle": "#8b949e",
        "status": "#3fb950",
        "button": "#21262d",
        "button_active": "#30363d",
        "button_disabled": "#161b22",
        "entry": "#0d1117",
        "selection": "#264f78",
        "user_label": "#58a6ff",
        "assistant_label": "#d2a8ff",
        "system_label": "#e3b341",
        "user_text": "#c9d1d9",
        "assistant_text": "#e6edf3",
        "system_text": "#8b949e",
    },
    "light": {
        "root": "#f5f7f8",
        "panel": "#ffffff",
        "border": "#d8dee4",
        "text": "#172026",
        "subtle": "#5b6670",
        "status": "#0f766e",
        "button": "#eef1f4",
        "button_active": "#dde3e8",
        "button_disabled": "#f4f5f6",
        "entry": "#ffffff",
        "selection": "#cfe8ff",
        "user_label": "#0f766e",
        "assistant_label": "#7c3aed",
        "system_label": "#b45309",
        "user_text": "#102a43",
        "assistant_text": "#243b53",
        "system_text": "#64748b",
    },
}


def normalize_theme(value):
    normalized = str(value or "").strip().lower()
    return normalized if normalized in GUI_THEMES else "dark"


def theme_button_label(theme):
    return "Light mode" if normalize_theme(theme) == "dark" else "Dark mode"


QUICK_COMMANDS = (
    ("Status", "jarvis status"),
    ("Verify", "jarvis verify"),
    ("Ollama On", "ollama on"),
    ("Ollama Off", "ollama off"),
    ("Light Model", "model recommend-light"),
    ("Eyes", "eyes status"),
    ("Self Learn", "self learning status"),
    ("Help", "help"),
)


def model_state_summary(
    config=None,
    language_module=None,
):
    configured = bool(
        getattr(
            config,
            "use_language_fallback",
            False,
        )
    )
    client = (
        getattr(
            language_module,
            "client",
            None,
        )
        if language_module
        else None
    )
    model = (
        getattr(client, "model", None)
        or getattr(
            config,
            "language_model",
            "unknown",
        )
    )
    available = bool(
        language_module
        and getattr(
            language_module,
            "available",
            False,
        )
    )
    busy = bool(
        client
        and getattr(client, "busy", False)
    )

    if configured and language_module and available:
        status = "Ollama ready"
        detail = (
            f"{model} is ready"
            + (" (busy)" if busy else "")
        )
    elif configured and language_module:
        status = "Ollama on"
        detail = (
            f"{model} is configured; run model check"
        )
    elif configured:
        status = "Ollama on"
        detail = (
            f"{model} will load after runtime restart"
        )
    else:
        status = "Ollama off"
        detail = (
            f"{model} is configured but not used"
        )

    return {
        "status": status,
        "detail": detail,
        "configured": configured,
        "available": available,
        "busy": busy,
        "model": model,
    }


def runtime_title(config=None):
    name = (
        getattr(config, "name", "Astra")
        or "Astra"
    )
    version = (
        getattr(config, "version", "unknown")
        or "unknown"
    )
    return f"{name} v{version}"


def low_hw_summary():
    return (
        "Low-RAM profile: Tkinter/no browser engine, 4K language context, "
        "throttled Eyes, one-model reuse; Eyes adds mss/Pillow/psutil."
    )
