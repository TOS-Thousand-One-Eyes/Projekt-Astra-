from commands.base import Command
from vision.image_inspector import ImageInspectionError, ImageInspector
from vision.semantic_vision import LocalVisionDescriber, VisionDescriptionError
from vision.screen_observer import ScreenObserverError


class VisionCommand(Command):
    help_text = (
        "- image inspect <path> - inspect a local PNG, JPEG, or GIF image\n"
        "- vision status / vision check - inspect or verify the local vision model\n"
        "- image describe <path> [question] - describe a local image with a vision-capable model\n"
        "- eyes status / eyes on / eyes off / eyes once - control passive local screen observation"
    )

    def __init__(
        self,
        inspector=None,
        describer=None,
        language_module=None,
        logger=None,
        observer=None,
        config=None,
    ):
        super().__init__(logger)
        self.inspector = inspector or ImageInspector()
        client = getattr(language_module, "client", None)
        source = "language" if client else "none"
        self.describer = describer or LocalVisionDescriber(
            client=client,
            inspector=self.inspector,
            source=source,
        )
        self.observer = observer
        self.config = config

    def handle(self, message, normalized):
        if normalized in (
            "vision",
            "vision status",
            "image model status",
        ):
            return self._status()
        if normalized in (
            "vision check",
            "image model check",
        ):
            return self._check()
        if normalized == "eyes status":
            return self._eyes_status()
        if normalized in ("eyes on", "eyes enable"):
            return self._eyes_on()
        if normalized in ("eyes off", "eyes disable"):
            return self._eyes_off()
        if normalized in (
            "eyes once",
            "eyes look",
            "eyes check",
        ):
            return self._eyes_once()
        if normalized.startswith("image inspect "):
            return self._inspect(
                message.strip()[len("image inspect "):]
            )
        if normalized.startswith("image describe "):
            return self._describe(
                message.strip()[len("image describe "):]
            )
        if normalized.startswith("describe image "):
            return self._describe(
                message.strip()[len("describe image "):]
            )
        if normalized.startswith("vision describe "):
            return self._describe(
                message.strip()[len("vision describe "):]
            )
        if normalized.startswith("see image "):
            return self._inspect(
                message.strip()[len("see image "):]
            )
        return None

    def _inspect(self, path):
        try:
            info = self.inspector.inspect(path)
        except FileNotFoundError as error:
            return str(error)
        except ImageInspectionError as error:
            return str(error)
        return (
            f"Image: {info['path']}\n"
            f"- format: {info['format']}\n"
            f"- size: {info['width']}x{info['height']}\n"
            f"- bytes: {info['bytes']}"
        )

    def _describe(self, text):
        path, prompt = split_path_and_prompt(text)
        if not path:
            return "Use: image describe <path> [question]"
        try:
            info = self.describer.describe(
                path,
                prompt=prompt,
            )
        except FileNotFoundError as error:
            return str(error)
        except (
            ImageInspectionError,
            VisionDescriptionError,
        ) as error:
            return str(error)
        return (
            f"Image description: {info['path']}\n"
            f"- format: {info['format']}\n"
            f"- size: {info['width']}x{info['height']}\n"
            f"- prompt: {info['prompt']}\n"
            f"{info['description']}"
        )

    def _status(self):
        client = getattr(
            self.describer, "client", None
        )
        configured = bool(
            client
            and callable(
                getattr(
                    client,
                    "generate_with_images",
                    None,
                )
            )
        )
        source = getattr(
            self.describer,
            "source",
            "vision" if configured else "none",
        )
        model = (
            getattr(client, "model", None)
            if configured
            else "none"
        )
        base_url = (
            getattr(client, "base_url", None)
            if configured
            else "none"
        )
        return "\n".join(
            [
                "Vision model status:",
                f"- configured: {str(configured).lower()}",
                f"- source: {source if configured else 'none'}",
                f"- model: {model or 'unknown'}",
                f"- base_url: {base_url or 'unknown'}",
            ]
        )

    def _check(self):
        client = getattr(
            self.describer, "client", None
        )
        if (
            not client
            or not callable(
                getattr(
                    client,
                    "generate_with_images",
                    None,
                )
            )
        ):
            return (
                "Vision model unavailable: no image-capable model client "
                "is configured."
            )
        if not callable(
            getattr(client, "ensure_available", None)
        ):
            return (
                "Vision model unavailable: configured client "
                "cannot be availability-checked."
            )
        try:
            client.ensure_available()
        except Exception as error:
            return f"Vision model unavailable: {error}"
        capability_reader = getattr(client, "capabilities", None)
        if callable(capability_reader):
            try:
                capabilities = {
                    str(value).strip().lower()
                    for value in capability_reader(getattr(client, "model", None))
                    if str(value).strip()
                }
            except Exception:
                capabilities = set()
            if capabilities and not capabilities.intersection(
                {"vision", "image", "images"}
            ):
                return (
                    f"Vision model unavailable: {getattr(client, 'model', 'unknown')} "
                    "does not advertise image/vision capability."
                )
        model = getattr(
            client, "model", "unknown"
        )
        base_url = getattr(
            client, "base_url", "unknown"
        )
        source = getattr(
            self.describer, "source", "vision"
        )
        if source == "language":
            return (
                f"Vision fallback client available: {model} at {base_url}; "
                "this confirms the shared local client is reachable, not a dedicated vision model."
            )
        return (
            f"Vision model available: {model} at {base_url} "
            f"(source: {source})."
        )

    def _eyes_status(self):
        if not self.observer:
            return "Eyes are not configured in this ASTRA runtime."
        status = self.observer.status()
        response = (
            "Eyes status:\n"
            f"- enabled: {str(status['enabled']).lower()}\n"
            f"- worker alive: {str(status['thread_alive']).lower()}\n"
            f"- vision ready: {str(status['vision_ready']).lower()}\n"
            f"- model: {status['model']}"
        )
        if status.get("vision_issue"):
            response += f"\n- issue: {status['vision_issue']}"
        return response

    def _eyes_on(self):
        if not self.observer:
            return "Eyes are not configured in this ASTRA runtime."
        try:
            self.observer.enable()
        except ScreenObserverError as error:
            return f"Eyes unavailable: {error}"
        persisted = self._persist_enabled(True)
        return (
            "Eyes enabled. Screenshots stay local/in RAM; "
            "semantic checks are throttled. "
            + (
                "Persisted to config.json."
                if persisted
                else "Runtime changed; config was not persisted."
            )
        )

    def _eyes_off(self):
        if not self.observer:
            return "Eyes are not configured in this ASTRA runtime."
        self.observer.disable()
        persisted = self._persist_enabled(False)
        return (
            "Eyes disabled. "
            + (
                "Persisted to config.json."
                if persisted
                else "Runtime changed; config was not persisted."
            )
        )

    def _eyes_once(self):
        if not self.observer:
            return "Eyes are not configured in this ASTRA runtime."
        try:
            result = self.observer.analyze_once(force=True)
        except ScreenObserverError as error:
            return f"Eyes unavailable: {error}"
        observation = result.get("observation") or result.get("reason") or "nothing noteworthy"
        return (
            f"Eyes one-shot: noteworthy={result.get('noteworthy', False)}, "
            f"confidence={result.get('confidence', 0)}\n"
            f"{observation}"
        )

    def _persist_enabled(self, enabled):
        persist = getattr(self.config, "persist", None)
        if callable(persist):
            return persist({"screen_observer_enabled": bool(enabled)})
        if self.config is not None:
            self.config.screen_observer_enabled = bool(enabled)
        return False


def split_path_and_prompt(text):
    stripped = str(text).strip()
    if not stripped:
        return "", ""
    for separator in (" -- ", " ? ", " :: "):
        if separator in stripped:
            path, prompt = stripped.split(
                separator,
                1,
            )
            return path.strip(), prompt.strip()
    return stripped, ""
