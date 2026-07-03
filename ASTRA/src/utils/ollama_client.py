import json
import re
import urllib.request

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
