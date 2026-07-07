from vision.image_inspector import ImageInspector


class VisionDescriptionError(Exception):
    pass


class LocalVisionDescriber:
    """Model-backed description for explicit local image files."""

    def __init__(self, client=None, inspector=None, source="vision"):
        self.client = client
        self.inspector = inspector or ImageInspector()
        self.source = source if client else "none"

    def describe(self, image_path, prompt=None):
        if not self.client or not callable(getattr(self.client, "generate_with_images", None)):
            raise VisionDescriptionError(
                "No vision-capable local model is configured. Use a local Ollama model that supports image input."
            )
        info = self.inspector.inspect(image_path)
        question = " ".join(str(prompt or "").split()) or (
            "Describe the image. Mention visible objects, text, layout, and uncertainty. "
            "Do not invent details that are not visible."
        )
        model_prompt = (
            "You are ASTRA's local vision layer.\n"
            f"Image metadata: {info['format']} {info['width']}x{info['height']} ({info['bytes']} bytes).\n"
            f"Task: {question}\n"
            "Answer concisely. If you are uncertain, say so."
        )
        try:
            description = self.client.generate_with_images(model_prompt, [info["path"]])
        except Exception as error:
            raise VisionDescriptionError(f"Vision description failed: {error}") from error
        return {
            "path": info["path"],
            "format": info["format"],
            "width": info["width"],
            "height": info["height"],
            "bytes": info["bytes"],
            "description": description,
            "prompt": question,
        }
