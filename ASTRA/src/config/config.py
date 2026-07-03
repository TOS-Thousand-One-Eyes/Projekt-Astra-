import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config.json"

UNKNOWN_VERSION = "0.0.0-unknown"

DEFAULTS = {
    "name": "Astra",
    "log_level": "INFO",
    "log_to_file": False,
    "check_for_updates": True,
    "use_language_fallback": False,
    "language_base_url": "http://localhost:11434",
    "language_model": "qwen3:4b",
}


class Config:

    def __init__(self, path=CONFIG_FILE):
        self.path = Path(path)
        settings = dict(DEFAULTS)
        settings.update(self._load())
        self.name = settings["name"]
        self.version = settings.get("version") or UNKNOWN_VERSION
        self.log_level = settings["log_level"]
        self.log_to_file = settings["log_to_file"]
        self.check_for_updates = settings["check_for_updates"]
        self.use_language_fallback = settings["use_language_fallback"]
        self.language_base_url = settings["language_base_url"]
        self.language_model = settings["language_model"]

    def _load(self):
        if not self.path.exists():
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
