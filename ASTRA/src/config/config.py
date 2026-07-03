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
}


class Config:

    def __init__(self, path=CONFIG_FILE):
        self.path = Path(path)
        self.load_warnings = []
        settings = dict(DEFAULTS)
        settings.update(self._load())
        self.name = settings["name"]
        self.version = settings.get("version") or UNKNOWN_VERSION
        if not settings.get("version"):
            self.load_warnings.append(
                f'{self.path.name} has no "version" value; update checks will be skipped until it\'s set.'
            )
        self.log_level = settings["log_level"]
        self.log_to_file = settings["log_to_file"]
        self.check_for_updates = settings["check_for_updates"]

    def _load(self):
        if not self.path.exists():
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except json.JSONDecodeError as error:
            self.load_warnings.append(f"{self.path.name} is not valid JSON ({error}); using defaults.")
            return {}
        except OSError as error:
            self.load_warnings.append(f"{self.path.name} could not be read ({error}); using defaults.")
            return {}
        if not isinstance(loaded, dict):
            self.load_warnings.append(f"{self.path.name} does not contain a JSON object; using defaults.")
            return {}
        return loaded
