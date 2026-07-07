import base64
import json
import re
import urllib.request
from pathlib import Path

# Reasoning models emit their <think> block at the start of the response
# (or, when the prompt template swallows the opening tag, as bare reasoning
# ending in a lone </think>). All three patterns are anchored to the leading
# position so a literal "<think>"/"</think>" later in a real answer (e.g. an
# answer *about* prompt formats) is kept as content, not eaten as markup.
LEADING_THINK_BLOCK_PATTERN = re.compile(r"\A\s*<think>.*?</think>", re.IGNORECASE | re.DOTALL)
LEADING_UNCLOSED_THINK_PATTERN = re.compile(r"\A\s*<think>.*", re.IGNORECASE | re.DOTALL)
LEADING_ORPHAN_THINK_CLOSE_PATTERN = re.compile(r"\A.*?</think>", re.IGNORECASE | re.DOTALL)


class OllamaClient:

    def __init__(
        self,
        base_url,
        model,
        health_timeout=3,
        generate_timeout=60,
        request_json=None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.health_timeout = health_timeout
        self.generate_timeout = generate_timeout
        self.request_json = request_json or self._request_json

    def ensure_available(self):
        payload = self.request_json(f"{self.base_url}/api/tags", timeout=self.health_timeout)
        models = payload.get("models")
        if not isinstance(models, list):
            raise ValueError("Ollama returned an invalid model list.")

        names = {
            item.get("model") or item.get("name")
            for item in models
            if isinstance(item, dict)
        }
        if self.model not in names:
            raise ValueError(f"Ollama model '{self.model}' is not available.")

    def list_models(self):
        payload = self.request_json(f"{self.base_url}/api/tags", timeout=self.health_timeout)
        models = payload.get("models")
        if not isinstance(models, list):
            raise ValueError("Ollama returned an invalid model list.")

        results = []
        for item in models:
            if not isinstance(item, dict):
                continue
            name = item.get("model") or item.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            details = item.get("details") if isinstance(item.get("details"), dict) else {}
            capabilities = item.get("capabilities") if isinstance(item.get("capabilities"), list) else []
            results.append(
                {
                    "name": name,
                    "size": item.get("size"),
                    "parameter_size": details.get("parameter_size"),
                    "capabilities": [str(capability) for capability in capabilities],
                }
            )
        return sorted(results, key=lambda model: model["name"].lower())

    def generate(self, prompt):
        payload = self.request_json(
            f"{self.base_url}/api/generate",
            method="POST",
            data={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=self.generate_timeout,
        )
        response = payload.get("response")
        if not isinstance(response, str):
            raise ValueError("Ollama returned an invalid response.")

        cleaned = self._strip_reasoning(response)
        if not cleaned:
            raise ValueError("Ollama returned an empty response.")
        return cleaned

    def generate_with_images(self, prompt, image_paths):
        images = [encode_image(path) for path in image_paths]
        if not images:
            raise ValueError("At least one image is required.")
        payload = self.request_json(
            f"{self.base_url}/api/generate",
            method="POST",
            data={
                "model": self.model,
                "prompt": prompt,
                "images": images,
                "stream": False,
            },
            timeout=self.generate_timeout,
        )
        response = payload.get("response")
        if not isinstance(response, str):
            raise ValueError("Ollama returned an invalid response.")

        cleaned = self._strip_reasoning(response)
        if not cleaned:
            raise ValueError("Ollama returned an empty response.")
        return cleaned

    @staticmethod
    def _strip_reasoning(response):
        cleaned = response
        while True:
            stripped = LEADING_THINK_BLOCK_PATTERN.sub("", cleaned, count=1)
            if stripped == cleaned:
                break
            cleaned = stripped
        cleaned = LEADING_UNCLOSED_THINK_PATTERN.sub("", cleaned, count=1)
        # A lone </think> is only reasoning markup when the opening tag never
        # appeared at all (the template-swallowed-opener case); if the response
        # had a real <think> anywhere, a remaining </think> is literal content.
        if "<think>" not in response.lower():
            cleaned = LEADING_ORPHAN_THINK_CLOSE_PATTERN.sub("", cleaned, count=1)
        return cleaned.strip()

    @staticmethod
    def _request_json(url, method="GET", data=None, timeout=3):
        payload = None
        headers = {}
        if data is not None:
            payload = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=payload, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)


def encode_image(path):
    image_path = Path(str(path).strip().strip('"'))
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    if not image_path.is_file():
        raise ValueError(f"Image path is not a file: {path}")
    return base64.b64encode(image_path.read_bytes()).decode("ascii")
