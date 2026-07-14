QUICK_COMMANDS = (
    ("Status", "jarvis status"),
    ("Verify", "jarvis verify"),
    ("Ollama On", "ollama on"),
    ("Ollama Off", "ollama off"),
    ("Light Model", "model recommend-light"),
    ("Help", "help"),
)


def model_state_summary(config=None, language_module=None):
    configured = bool(getattr(config, "use_language_fallback", False))
    client = getattr(language_module, "client", None) if language_module else None
    model = getattr(client, "model", None) or getattr(config, "language_model", "unknown")
    available = bool(language_module and getattr(language_module, "available", False))

    if configured and language_module and available:
        status = "Ollama ready"
        detail = f"{model} is available in this session"
    elif configured and language_module:
        status = "Ollama on"
        detail = f"{model} is configured; run model check"
    elif configured:
        status = "Ollama on"
        detail = f"{model} will load after runtime restart"
    else:
        status = "Ollama off"
        detail = f"{model} is configured but not used"

    return {
        "status": status,
        "detail": detail,
        "configured": configured,
        "available": available,
        "model": model,
    }


def runtime_title(config=None):
    name = getattr(config, "name", "Astra") or "Astra"
    version = getattr(config, "version", "unknown") or "unknown"
    return f"{name} v{version}"


def low_hw_summary():
    return "Tkinter GUI, no browser engine, no extra runtime dependencies."

