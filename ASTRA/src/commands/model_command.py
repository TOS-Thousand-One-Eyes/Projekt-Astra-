import json
import os

from commands.base import Command


class ModelCommand(Command):
    help_text = (
        "- model status / model list / model check - inspect or verify the local language model\n"
        "- model use <name> - switch to an installed local Ollama model\n"
        "- model smoke - run a short local model smoke test\n"
        "- model ask <prompt> - ask the local model directly"
    )

    SMOKE_PROMPT = "Reply with ASTRA-OK only."

    def __init__(self, language_module=None, config=None, logger=None):
        super().__init__(logger)
        self.language_module = language_module
        self.config = config

    def handle(self, message, normalized):
        if normalized in ("model", "model status", "model runtime"):
            return self._status()
        if normalized in ("model list", "models", "ollama models"):
            return self._list()
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
            return "Local model status:\n- configured: false"

        available = bool(getattr(self.language_module, "available", False))
        return "\n".join(
            [
                "Local model status:",
                "- configured: true",
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
            data["use_language_fallback"] = True
            data["language_model"] = model_name
            tmp_path = path.with_suffix(path.suffix + ".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            os.replace(tmp_path, path)
        except (OSError, json.JSONDecodeError) as error:
            if self.logger:
                self.logger.warning(f"Failed to persist model config: {error}")
            return False
        self.config.use_language_fallback = True
        self.config.language_model = model_name
        return True
