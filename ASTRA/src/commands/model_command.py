import json
import os
import threading
import uuid

from commands.base import Command


class ModelCommand(Command):
    help_text = (
        "- model status / model list / model check - inspect or verify the Ollama model\n"
        "- model on / model off - enable or disable Ollama fallback\n"
        "- model use <name> - switch immediately to an installed Ollama model\n"
        "- model recommend / model recommend-balanced - recommendation for this ASTRA build\n"
        "- model recommend-light - lower-HW recommendation\n"
        "- model smoke - run a short model smoke test\n"
        "- model ask <prompt> - ask the current model directly"
    )

    SMOKE_PROMPT = "Reply with ASTRA-OK only."

    BALANCED_RECOMMENDATION = {
        "recommended": "gemma3:4b",
        "recommended_size": "3.3GB",
        "why": (
            "one compact multilingual model can handle normal chat and image input, "
            "so ASTRA can reuse it for local Eyes without keeping two large models resident"
        ),
    }

    LIGHTWEIGHT_RECOMMENDATION = {
        "recommended": "gemma3:1b",
        "recommended_size": "815MB",
        "same_family": "llama3.2:1b",
        "same_family_size": "1.3GB",
    }

    def __init__(
        self,
        language_module=None,
        config=None,
        logger=None,
        screen_observer=None,
    ):
        super().__init__(logger)
        self.language_module = language_module
        self.config = config
        self.screen_observer = screen_observer

    def handle(self, message, normalized):
        if normalized in ("model", "model status", "model runtime"):
            return self._status()
        if normalized in ("model list", "models", "ollama models"):
            return self._list()
        if normalized in (
            "model on",
            "model enable",
            "ollama on",
            "ollama enable",
        ):
            return self._set_fallback_enabled(True)
        if normalized in (
            "model off",
            "model disable",
            "ollama off",
            "ollama disable",
        ):
            return self._set_fallback_enabled(False)
        if normalized in (
            "model recommend",
            "model recommend-balanced",
            "model recommend balanced",
            "model balanced",
        ):
            return self._recommend_balanced_model()
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
            model_name = message.strip()[len("model use "):].strip()
            return self._use(model_name)
        if normalized == "model check":
            return self._check()
        if normalized == "model smoke":
            return self._smoke()
        if normalized == "model ask":
            return "Usage: model ask <prompt>"
        if normalized.startswith("model ask "):
            prompt = message.strip()[len("model ask "):].strip()
            return self._ask(prompt)
        return None

    def _status(self):
        if not self.language_module:
            configured = bool(
                getattr(self.config, "use_language_fallback", False)
            )
            lines = [
                "Model status:",
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

        available = bool(
            getattr(self.language_module, "available", False)
        )
        configured = bool(
            getattr(self.config, "use_language_fallback", True)
        )
        busy = bool(
            getattr(self._client(), "busy", False)
        )
        return "\n".join(
            [
                "Model status:",
                f"- configured: {str(configured).lower()}",
                "- session module: true",
                f"- available: {str(available).lower()}",
                f"- busy: {str(busy).lower()}",
                f"- model: {self._model_name()}",
                f"- endpoint: {self._base_url()}",
            ]
        )

    def _list(self):
        client = self._client()
        if not client or not callable(
            getattr(client, "list_models", None)
        ):
            return (
                "Local model client cannot list Ollama models "
                "in this ASTRA session."
            )
        try:
            models = client.list_models()
        except Exception as error:
            return f"Local model list unavailable: {error}"
        if not models:
            return "Installed/registered Ollama models:\n- none"

        lines = ["Installed/registered Ollama models:"]
        for item in models:
            details = []
            if item.get("parameter_size"):
                details.append(str(item["parameter_size"]))
            if item.get("capabilities"):
                details.append(
                    "capabilities="
                    + ",".join(item["capabilities"])
                )
            if item.get("size"):
                try:
                    details.append(
                        f"size={float(item['size']) / (1024**3):.2f}GB"
                    )
                except (TypeError, ValueError):
                    pass
            suffix = f" ({'; '.join(details)})" if details else ""
            current = (
                " [current]"
                if _same_model_name(
                    item["name"], self._model_name()
                )
                else ""
            )
            cloud = (
                " [cloud]"
                if ":cloud" in item["name"].lower()
                else ""
            )
            lines.append(
                f"- {item['name']}{current}{cloud}{suffix}"
            )
        return "\n".join(lines)

    def _use(self, model_name):
        model_name = " ".join(str(model_name).split())
        if not model_name:
            return "Usage: model use <installed-model-name>"

        client = self._client()
        if (
            not client
            or not callable(getattr(client, "list_models", None))
        ):
            return (
                "Local model client cannot switch models "
                "in this ASTRA session."
            )

        try:
            models = client.list_models()
        except Exception as error:
            return f"Local model list unavailable: {error}"

        available = {
            item["name"]
            for item in models
        }
        actual_name = next(
            (
                name
                for name in available
                if _same_model_name(name, model_name)
            ),
            None,
        )
        if not actual_name:
            if not available:
                return (
                    f"Model '{model_name}' is not installed/registered. "
                    "No Ollama models are available."
                )
            return (
                f"Model '{model_name}' is not installed/registered. "
                "Available models: "
                + ", ".join(sorted(available))
            )

        previous_model = getattr(client, "model", None)
        previous_available = bool(
            getattr(self.language_module, "available", False)
        )
        client.model = actual_name
        self.language_module.available = False

        try:
            client.ensure_available()
        except Exception as error:
            client.model = previous_model
            self.language_module.available = previous_available
            return (
                f"Model switch failed; kept {previous_model or 'previous model'}: "
                f"{error}"
            )

        self.language_module.available = True
        persisted = self._persist_language_model(actual_name)
        suffix = (
            "Persisted to config.json."
            if persisted
            else "Runtime switched; config was not persisted."
        )
        eyes_note = self._sync_shared_eyes_after_switch(
            actual_name,
            models,
            client,
        )
        return (
            f"Model switched and ready: {actual_name}. {suffix}"
            + (f" {eyes_note}" if eyes_note else "")
        )

    def _sync_shared_eyes_after_switch(
        self,
        model_name,
        models,
        client,
    ):
        observer = self.screen_observer
        if not observer:
            return ""

        describer = getattr(observer, "describer", None)
        observer_client = getattr(describer, "client", None)
        if observer_client is not client:
            # Dedicated vision model: language switching must not affect Eyes.
            return ""

        capabilities = set()
        capability_reader = getattr(client, "capabilities", None)
        if callable(capability_reader):
            try:
                capabilities = {
                    str(value).strip().lower()
                    for value in capability_reader(model_name)
                    if str(value).strip()
                }
            except Exception:
                capabilities = set()
        else:
            item = next(
                (
                    model
                    for model in models
                    if _same_model_name(
                        model.get("name"),
                        model_name,
                    )
                ),
                None,
            )
            if not item:
                return ""
            capabilities = {
                str(value).strip().lower()
                for value in item.get("capabilities", [])
                if str(value).strip()
            }
        if not capabilities:
            return (
                "Eyes capability metadata is unknown for this model; "
                "use `eyes once` to verify image support."
                if getattr(observer, "enabled", False)
                else ""
            )

        if capabilities.intersection({"vision", "image", "images"}):
            return ""

        if getattr(observer, "enabled", False):
            disable = getattr(observer, "disable", None)
            if callable(disable):
                disable()
            return (
                "Eyes were disabled because this model does not advertise "
                "vision/image capability."
            )
        return "This model does not advertise vision/image capability; Eyes stay off."

    def _set_fallback_enabled(self, enabled):
        persisted = self._persist_language_fallback(enabled)
        persist_note = (
            "Persisted to config.json."
            if persisted
            else "Config was not persisted."
        )

        if not enabled:
            if self.language_module:
                stop = getattr(
                    self.language_module, "stop", None
                )
                if callable(stop):
                    stop()
                else:
                    self.language_module.available = False
            return (
                "Ollama fallback disabled. "
                f"{persist_note} This session will not use the model "
                "for unmatched chat."
            )

        if not self.language_module:
            return (
                "Ollama fallback enabled. "
                f"{persist_note} Restart ASTRA to create the language module, "
                "then run `model check`."
            )

        ok, message = self._ensure_available()
        if not ok:
            return (
                f"Ollama fallback enabled. {persist_note} {message}"
            )
        return (
            "Ollama fallback enabled. "
            f"{persist_note} Runtime available: "
            f"{self._model_name()} at {self._base_url()}."
        )

    def _recommend_balanced_model(self):
        rec = self.BALANCED_RECOMMENDATION
        return "\n".join(
            [
                "Balanced ASTRA model recommendation:",
                f"- recommended: {rec['recommended']} ({rec['recommended_size']})",
                f"- why: {rec['why']}",
                "- fit: intended for the current 8 GB RAM / 2 GB VRAM class of machine with a modest context window",
                f"- install: ollama pull {rec['recommended']}",
                f"- switch: model use {rec['recommended']}",
                "- note: a 4B model is still much weaker than frontier cloud models, but it is a practical fully-offline baseline",
            ]
        )

    def _recommend_lightweight_model(self):
        rec = self.LIGHTWEIGHT_RECOMMENDATION
        return "\n".join(
            [
                "Lightweight model recommendation:",
                f"- recommended: {rec['recommended']} ({rec['recommended_size']}, text)",
                "- why: much lower RAM pressure and faster CPU inference",
                "- tradeoff: substantially weaker reasoning and language quality",
                f"- install: ollama pull {rec['recommended']}",
                f"- switch: model use {rec['recommended']}",
                (
                    f"- same-family option: {rec['same_family']} "
                    f"({rec['same_family_size']})"
                ),
            ]
        )

    def _check(self):
        ok, message = self._ensure_available()
        if not ok:
            return message
        return (
            f"Model available: {self._model_name()} "
            f"at {self._base_url()}"
        )

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
            return "Model did not return a response."
        return "Model response:\n" + response

    def _ensure_available(self):
        if not self.language_module:
            return False, (
                "Model module is not configured for this ASTRA session."
            )

        client = self._client()
        if not client or not hasattr(
            client, "ensure_available"
        ):
            return False, (
                "Model client is not configured for this ASTRA session."
            )

        try:
            client.ensure_available()
        except Exception as error:
            self.language_module.available = False
            if self.logger:
                self.logger.warning(
                    f"Model availability check failed: {error}"
                )
            return False, f"Model unavailable: {error}"

        self.language_module.available = True
        return True, "Model available."

    def _model_name(self):
        client = self._client()
        return getattr(client, "model", None) or "unknown"

    def _base_url(self):
        client = self._client()
        return getattr(client, "base_url", None) or "unknown"

    def _client(self):
        return (
            getattr(self.language_module, "client", None)
            if self.language_module
            else None
        )

    def _persist_language_model(self, model_name):
        persisted = self._persist_config(
            {
                "use_language_fallback": True,
                "language_model": model_name,
            }
        )
        self._set_config_value(
            "use_language_fallback", True
        )
        self._set_config_value(
            "language_model", model_name
        )
        return persisted

    def _persist_language_fallback(self, enabled):
        persisted = self._persist_config(
            {"use_language_fallback": bool(enabled)}
        )
        self._set_config_value(
            "use_language_fallback", bool(enabled)
        )
        return persisted

    def _persist_config(self, updates):
        path = getattr(self.config, "path", None)
        if not path:
            return False
        try:
            data = {}
            if path.exists():
                with open(
                    path, "r", encoding="utf-8-sig"
                ) as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
            data.update(updates)
            tmp_path = path.with_suffix(
                f"{path.suffix}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp"
            )
            with open(
                tmp_path, "w", encoding="utf-8"
            ) as f:
                json.dump(
                    data,
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
                f.write("\n")
            os.replace(tmp_path, path)
        except (
            OSError,
            json.JSONDecodeError,
        ) as error:
            if self.logger:
                self.logger.warning(
                    f"Failed to persist model config: {error}"
                )
            return False
        return True

    def _set_config_value(self, key, value):
        if self.config:
            setattr(self.config, key, value)


def _same_model_name(a, b):
    a = str(a or "").strip()
    b = str(b or "").strip()
    if a == b:
        return True
    if ":" not in a and b == a + ":latest":
        return True
    if ":" not in b and a == b + ":latest":
        return True
    return False
