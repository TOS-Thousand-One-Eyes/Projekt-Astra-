import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config.json"

DEFAULTS = {
    "name": "Astra",
    "version": "0.0.8",
    "log_level": "INFO",
    "log_to_file": False,
    "check_for_updates": True,
}


class Config:

    def __init__(self, path=CONFIG_FILE):
        self.path = Path(path)
        settings = dict(DEFAULTS)
        settings.update(self._load())
        self.name = settings["name"]
        self.version = settings["version"]
        self.log_level = settings["log_level"]
        self.log_to_file = settings["log_to_file"]
        self.check_for_updates = settings["check_for_updates"]

    def _load(self):
        if not self.path.exists():
            return {}
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)
