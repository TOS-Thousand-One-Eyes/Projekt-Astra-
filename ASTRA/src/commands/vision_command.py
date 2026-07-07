from commands.base import Command
from vision.image_inspector import ImageInspectionError, ImageInspector
from vision.semantic_vision import LocalVisionDescriber, VisionDescriptionError


class VisionCommand(Command):
    help_text = (
        "- image inspect <path> - inspect a local PNG, JPEG, or GIF image\n"
        "- vision status / vision check - inspect or verify the local vision model\n"
        "- image describe <path> [question] - describe a local image with a vision-capable local model"
    )

    def __init__(self, inspector=None, describer=None, language_module=None, logger=None):
        super().__init__(logger)
        self.inspector = inspector or ImageInspector()
        client = getattr(language_module, "client", None)
        source = "language" if client else "none"
        self.describer = describer or LocalVisionDescriber(client=client, inspector=self.inspector, source=source)

    def handle(self, message, normalized):
        if normalized in ("vision", "vision status", "image model status"):
            return self._status()
        if normalized in ("vision check", "image model check"):
            return self._check()
        if normalized.startswith("image inspect "):
            return self._inspect(message.strip()[len("image inspect "):])
        if normalized.startswith("image describe "):
            return self._describe(message.strip()[len("image describe "):])
        if normalized.startswith("describe image "):
            return self._describe(message.strip()[len("describe image "):])
        if normalized.startswith("vision describe "):
            return self._describe(message.strip()[len("vision describe "):])
        if normalized.startswith("see image "):
            return self._inspect(message.strip()[len("see image "):])
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
            info = self.describer.describe(path, prompt=prompt)
        except FileNotFoundError as error:
            return str(error)
        except (ImageInspectionError, VisionDescriptionError) as error:
            return str(error)
        return (
            f"Image description: {info['path']}\n"
            f"- format: {info['format']}\n"
            f"- size: {info['width']}x{info['height']}\n"
            f"- prompt: {info['prompt']}\n"
            f"{info['description']}"
        )

    def _status(self):
        client = getattr(self.describer, "client", None)
        configured = bool(client and callable(getattr(client, "generate_with_images", None)))
        source = getattr(self.describer, "source", "vision" if configured else "none")
        model = getattr(client, "model", None) if configured else "none"
        base_url = getattr(client, "base_url", None) if configured else "none"
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
        client = getattr(self.describer, "client", None)
        if not client or not callable(getattr(client, "generate_with_images", None)):
            return (
                "Vision model unavailable: no image-capable local model client is configured. "
                "Set use_vision_model=true with a vision-capable Ollama model."
            )
        if not callable(getattr(client, "ensure_available", None)):
            return "Vision model unavailable: configured client cannot be availability-checked."
        try:
            client.ensure_available()
        except Exception as error:
            return f"Vision model unavailable: {error}"
        model = getattr(client, "model", "unknown")
        base_url = getattr(client, "base_url", "unknown")
        source = getattr(self.describer, "source", "vision")
        if source == "language":
            return (
                f"Vision fallback client available: {model} at {base_url} (source: language). "
                "This is not a dedicated vision model; run `image describe <path>` or configure `use_vision_model`."
            )
        return f"Vision model available: {model} at {base_url} (source: {source})."


def split_path_and_prompt(text):
    stripped = str(text).strip()
    if not stripped:
        return "", ""
    for separator in (" -- ", " ? ", " :: "):
        if separator in stripped:
            path, prompt = stripped.split(separator, 1)
            return path.strip(), prompt.strip()
    return stripped, ""
