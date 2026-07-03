import json
import re
import urllib.request

THINK_BLOCK_PATTERN = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
UNCLOSED_THINK_PATTERN = re.compile(r"<think>.*", re.IGNORECASE | re.DOTALL)
ORPHAN_THINK_CLOSE_PATTERN = re.compile(r"^.*?</think>", re.IGNORECASE | re.DOTALL)


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

        cleaned = THINK_BLOCK_PATTERN.sub("", response)
        cleaned = UNCLOSED_THINK_PATTERN.sub("", cleaned)
        cleaned = ORPHAN_THINK_CLOSE_PATTERN.sub("", cleaned).strip()
        if not cleaned:
            raise ValueError("Ollama returned an empty response.")
        return cleaned

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
