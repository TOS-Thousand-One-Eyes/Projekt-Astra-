import base64
import json
import re
import threading
import urllib.request
from pathlib import Path

LEADING_THINK_BLOCK_PATTERN = re.compile(
    r"\A\s*<think>.*?</think>", re.IGNORECASE | re.DOTALL
)
LEADING_UNCLOSED_THINK_PATTERN = re.compile(
    r"\A\s*<think>.*", re.IGNORECASE | re.DOTALL
)
LEADING_ORPHAN_THINK_CLOSE_PATTERN = re.compile(
    r"\A.*?</think>", re.IGNORECASE | re.DOTALL
)


class OllamaClient:

    def __init__(
        self,
        base_url,
        model,
        health_timeout=3,
        generate_timeout=60,
        request_json=None,
        options=None,
        keep_alive=None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.health_timeout = health_timeout
        self.generate_timeout = generate_timeout
        self.request_json = request_json or self._request_json
        self.options = dict(options or {})
        self.keep_alive = keep_alive
        self._request_lock = threading.Lock()
        self._busy = threading.Event()

    @property
    def busy(self):
        return self._busy.is_set()

    def ensure_available(self):
        payload = self._serialized_request(
            f"{self.base_url}/api/tags", timeout=self.health_timeout
        )
        models = payload.get("models")
        if not isinstance(models, list):
            raise ValueError("Ollama returned an invalid model list.")

        names = {
            item.get("model") or item.get("name")
            for item in models
            if isinstance(item, dict)
        }
        if not any(_same_model_name(self.model, name) for name in names if name):
            raise ValueError(f"Ollama model '{self.model}' is not available.")

    def show_model(self, model=None):
        target = str(model or self.model).strip()
        if not target:
            raise ValueError("Model name cannot be empty.")
        payload = self._serialized_request(
            f"{self.base_url}/api/show",
            method="POST",
            data={"model": target, "verbose": False},
            timeout=self.health_timeout,
        )
        if not isinstance(payload, dict):
            raise ValueError("Ollama returned invalid model details.")
        return payload

    def capabilities(self, model=None):
        payload = self.show_model(model=model)
        values = payload.get("capabilities")
        if not isinstance(values, list):
            return []
        return [
            str(value).strip().lower()
            for value in values
            if str(value).strip()
        ]

    def list_models(self):
        payload = self._serialized_request(
            f"{self.base_url}/api/tags", timeout=self.health_timeout
        )
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
            capabilities = (
                item.get("capabilities")
                if isinstance(item.get("capabilities"), list)
                else []
            )
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
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        self._add_generation_settings(data)
        payload = self._serialized_request(
            f"{self.base_url}/api/generate",
            method="POST",
            data=data,
            timeout=self.generate_timeout,
        )
        return self._response_text(payload)

    def generate_with_images(self, prompt, image_paths):
        images = [encode_image(path) for path in image_paths]
        return self._generate_with_encoded_images(prompt, images)

    def generate_with_image_bytes(self, prompt, image_bytes):
        images = []
        for value in image_bytes:
            if not isinstance(value, (bytes, bytearray)) or not value:
                raise ValueError("Image bytes must be non-empty bytes.")
            images.append(base64.b64encode(bytes(value)).decode("ascii"))
        return self._generate_with_encoded_images(prompt, images)

    def _generate_with_encoded_images(self, prompt, images):
        if not images:
            raise ValueError("At least one image is required.")
        data = {
            "model": self.model,
            "prompt": prompt,
            "images": images,
            "stream": False,
        }
        self._add_generation_settings(data)
        payload = self._serialized_request(
            f"{self.base_url}/api/generate",
            method="POST",
            data=data,
            timeout=self.generate_timeout,
        )
        return self._response_text(payload)

    def _add_generation_settings(self, data):
        if self.options:
            data["options"] = dict(self.options)
        if self.keep_alive is not None:
            data["keep_alive"] = self.keep_alive

    def _serialized_request(self, *args, **kwargs):
        with self._request_lock:
            self._busy.set()
            try:
                return self.request_json(*args, **kwargs)
            finally:
                self._busy.clear()

    def _response_text(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("Ollama returned an invalid response payload.")
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
        request = urllib.request.Request(
            url, data=payload, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            error.close()
            raise


def _same_model_name(expected, actual):
    expected = str(expected or "").strip()
    actual = str(actual or "").strip()
    if expected == actual:
        return True
    if ":" not in expected and actual == expected + ":latest":
        return True
    if ":" not in actual and expected == actual + ":latest":
        return True
    return False


def encode_image(path):
    image_path = Path(str(path).strip().strip('"'))
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    if not image_path.is_file():
        raise ValueError(f"Image path is not a file: {path}")
    return base64.b64encode(image_path.read_bytes()).decode("ascii")
