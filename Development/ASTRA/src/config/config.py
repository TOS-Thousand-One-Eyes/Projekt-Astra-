import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config.json"

DEFAULTS = {
    "name": "Astra",
    "version": "0.0.7",
}


class Config:

    def __init__(self, path=CONFIG_FILE):
        self.path = Path(path)
        settings = dict(DEFAULTS)
        settings.update(self._load())
        self.name = settings["name"]
        self.version = settings["version"]

    def _load(self):
        if not self.path.exists():
            return {}
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)
