import json
import os

from commands.base import Command


class ModelCommand(Command):
    help_text = (
        "- model status / model list / model check - inspect or verify the local language model\n"
        "- model on / model off - enable or disable the local Ollama fallback\n"
        "- model use <name> - switch to an installed local Ollama model\n"
        "- model recommend-light - show a lower-HW Ollama model recommendation\n"
        "- model smoke - run a short local model smoke test\n"
        "- model ask <prompt> - ask the local model directly"
    )

    SMOKE_PROMPT = "Reply with ASTRA-OK only."
    LIGHTWEIGHT_RECOMMENDATION = {
        "recommended": "gemma3:1b",
        "recommended_size": "815MB",
        "current_reference": "llama3.2:3b",
        "current_reference_size": "2.0GB",
        "same_family": "llama3.2:1b",
        "same_family_size": "1.3GB",
    }

    def __init__(self, language_module=None, config=None, logger=None):
        super().__init__(logger)
        self.language_module = language_module
        self.config = config

    def handle(self, message, normalized):
        if normalized in ("model", "model status", "model runtime"):
            return self._status()
        if normalized in ("model list", "models", "ollama models"):
            return self._list()
        if normalized in ("model on", "model enable", "ollama on", "ollama enable"):
            return self._set_fallback_enabled(True)
        if normalized in ("model off", "model disable", "ollama off", "ollama disable"):
            return self._set_fallback_enabled(False)
        if normalized in (
            "model recommend-light",
            "model recommend light",
            "model lightweight",
            "model light",
            "model low-hw",
            "ollama light",
        ):
            return self._recommend_lightweight_model()
        if normalized == "model use":
            return "Usage: model use <installed-model-name>"
        if normalized.startswith("model use "):
            model_name = message.strip()[len("model use ") :].strip()
            return self._use(model_name)
        if normalized == "model check":
            return self._check()
        if normalized == "model smoke":
            return self._smoke()
        if normalized == "model ask":
            return "Usage: model ask <prompt>"
        if normalized.startswith("model ask "):
            prompt = message.strip()[len("model ask ") :].strip()
            return self._ask(prompt)
        return None

    def _status(self):
        if not self.language_module:
            configured = bool(getattr(self.config, "use_language_fallback", False))
            lines = [
                "Local model status:",
                f"- configured: {str(configured).lower()}",
                "- session module: false",
            ]
            if self.config:
                lines.extend(
                    [
                        f"- model: {getattr(self.config, 'language_model', 'unknown')}",
                        f"- endpoint: {getattr(self.config, 'language_base_url', 'unknown')}",
                    ]
                )
            return "\n".join(lines)

        available = bool(getattr(self.language_module, "available", False))
        configured = bool(getattr(self.config, "use_language_fallback", True))
        return "\n".join(
            [
                "Local model status:",
                f"- configured: {str(configured).lower()}",
                "- session module: true",
                f"- available: {str(available).lower()}",
                f"- model: {self._model_name()}",
                f"- endpoint: {self._base_url()}",
            ]
        )

    def _list(self):
        client = self._client()
        if not client or not callable(getattr(client, "list_models", None)):
            return "Local model client cannot list Ollama models in this ASTRA session."
        try:
            models = client.list_models()
        except Exception as error:
            return f"Local model list unavailable: {error}"
        if not models:
            return "Installed Ollama models:\n- none"
        lines = ["Installed Ollama models:"]
        for item in models:
            details = []
            if item.get("parameter_size"):
                details.append(str(item["parameter_size"]))
            if item.get("capabilities"):
                details.append("capabilities=" + ",".join(item["capabilities"]))
            suffix = f" ({'; '.join(details)})" if details else ""
            current = " [current]" if item["name"] == self._model_name() else ""
            lines.append(f"- {item['name']}{current}{suffix}")
        return "\n".join(lines)

    def _use(self, model_name):
        model_name = " ".join(str(model_name).split())
        if not model_name:
            return "Usage: model use <installed-model-name>"
        client = self._client()
        if not client or not callable(getattr(client, "list_models", None)):
            return "Local model client cannot switch models in this ASTRA session."
        try:
            models = client.list_models()
        except Exception as error:
            return f"Local model list unavailable: {error}"
        available = {item["name"] for item in models}
        if model_name not in available:
            if not available:
                return f"Model '{model_name}' is not installed. No local Ollama models are available."
            return (
                f"Model '{model_name}' is not installed. Available models: "
                + ", ".join(sorted(available))
            )

        client.model = model_name
        if self.language_module:
            self.language_module.available = False
        persisted = self._persist_language_model(model_name)
        suffix = " Persisted to config.json." if persisted else " Runtime switched; config was not persisted."
        return f"Configured local model: {model_name}.{suffix} Run `model check` or `model smoke`."

    def _set_fallback_enabled(self, enabled):
        persisted = self._persist_language_fallback(enabled)
        persist_note = "Persisted to config.json." if persisted else "Config was not persisted."

        if not enabled:
            if self.language_module:
                stop = getattr(self.language_module, "stop", None)
                if callable(stop):
                    stop()
                else:
                    self.language_module.available = False
            return (
                "Local Ollama fallback disabled. "
                f"{persist_note} This session will not use the local model for unmatched chat."
            )

        if not self.language_module:
            return (
                "Local Ollama fallback enabled. "
                f"{persist_note} Restart ASTRA to create the Ollama language module, "
                "then run `model check`."
            )

        ok, message = self._ensure_available()
        if not ok:
            return f"Local Ollama fallback enabled. {persist_note} {message}"
        return (
            "Local Ollama fallback enabled. "
            f"{persist_note} Runtime available: {self._model_name()} at {self._base_url()}."
        )

    def _recommend_lightweight_model(self):
        rec = self.LIGHTWEIGHT_RECOMMENDATION
        return "\n".join(
            [
                "Lightweight local model recommendation:",
                f"- recommended: {rec['recommended']} ({rec['recommended_size']}, text)",
                (
                    f"- why: it is under half the published Ollama size of "
                    f"{rec['current_reference']} ({rec['current_reference_size']})"
                ),
                "- tradeoff: lower memory and disk use, but weaker answers and shorter 32K context",
                f"- install outside ASTRA: ollama pull {rec['recommended']}",
                f"- switch after install: model use {rec['recommended']}",
                (
                    f"- same-family option: {rec['same_family']} ({rec['same_family_size']}); "
                    "easier transition, but not quite half the size"
                ),
            ]
        )

    def _check(self):
        ok, message = self._ensure_available()
        if not ok:
            return message
        return f"Local model available: {self._model_name()} at {self._base_url()}"

    def _smoke(self):
        return self._ask(self.SMOKE_PROMPT)

    def _ask(self, prompt):
        if not prompt:
            return "Usage: model ask <prompt>"

        ok, message = self._ensure_available()
        if not ok:
            return message

        response = self.language_module.respond(prompt)
        if not response:
            return "Local model did not return a response."
        return "Model response:\n" + response

    def _ensure_available(self):
        if not self.language_module:
            return False, "Local model module is not configured for this ASTRA session."

        client = self._client()
        if not client or not hasattr(client, "ensure_available"):
            return False, "Local model client is not configured for this ASTRA session."

        try:
            client.ensure_available()
        except Exception as error:
            self.language_module.available = False
            if self.logger:
                self.logger.warning(f"Local model availability check failed: {error}")
            return False, f"Local model unavailable: {error}"

        self.language_module.available = True
        return True, "Local model available."

    def _model_name(self):
        client = self._client()
        return getattr(client, "model", None) or "unknown"

    def _base_url(self):
        client = self._client()
        return getattr(client, "base_url", None) or "unknown"

    def _client(self):
        return getattr(self.language_module, "client", None) if self.language_module else None

    def _persist_language_model(self, model_name):
        persisted = self._persist_config(
            {
                "use_language_fallback": True,
                "language_model": model_name,
            }
        )
        self._set_config_value("use_language_fallback", True)
        self._set_config_value("language_model", model_name)
        return persisted

    def _persist_language_fallback(self, enabled):
        persisted = self._persist_config({"use_language_fallback": bool(enabled)})
        self._set_config_value("use_language_fallback", bool(enabled))
        return persisted

    def _persist_config(self, updates):
        path = getattr(self.config, "path", None)
        if not path:
            return False
        try:
            data = {}
            if path.exists():
                with open(path, "r", encoding="utf-8-sig") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
            data.update(updates)
            tmp_path = path.with_suffix(path.suffix + ".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            os.replace(tmp_path, path)
        except (OSError, json.JSONDecodeError) as error:
            if self.logger:
                self.logger.warning(f"Failed to persist model config: {error}")
            return False
        return True

    def _set_config_value(self, key, value):
        if self.config:
            setattr(self.config, key, value)
