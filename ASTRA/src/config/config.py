import json
from pathlib import Path

from utils.logger import LEVELS

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
    "language_generate_timeout": 240,
    "use_vision_model": False,
    "vision_base_url": "http://localhost:11434",
    "vision_model": "llava:latest",
    "vision_generate_timeout": 240,
}


class Config:

    def __init__(self, path=CONFIG_FILE):
        self.path = Path(path)
        self.load_warnings = []
        settings = dict(DEFAULTS)
        settings.update(self._validated(self._load()))
        self.name = settings["name"]
        self.version = settings.get("version") or UNKNOWN_VERSION
        if not settings.get("version"):
            self.load_warnings.append(
                f'{self.path.name} has no "version" value; Astra can\'t tell '
                f"whether it's up to date until it's set (if update checks "
                f"are enabled, they still report the latest available version)."
            )
        self.log_level = self._validated_log_level(settings["log_level"])
        self.log_to_file = settings["log_to_file"]
        self.check_for_updates = settings["check_for_updates"]
        self.use_language_fallback = settings["use_language_fallback"]
        self.language_base_url = settings["language_base_url"]
        self.language_model = settings["language_model"]
        self.language_generate_timeout = settings["language_generate_timeout"]
        self.use_vision_model = settings["use_vision_model"]
        self.vision_base_url = settings["vision_base_url"]
        self.vision_model = settings["vision_model"]
        self.vision_generate_timeout = settings["vision_generate_timeout"]

    def _validated_log_level(self, value):
        # Logger would silently coerce an unknown level to INFO; catch it
        # here instead so the fallback is observable (and accept any casing).
        normalized = value.strip().upper()
        if normalized in LEVELS:
            return normalized
        self.load_warnings.append(
            f'{self.path.name} has an unknown "log_level" value ({value!r}); '
            f'expected one of {", ".join(LEVELS)}. Using "INFO".'
        )
        return "INFO"

    def _validated(self, loaded):
        valid = {}
        for key, value in loaded.items():
            default = DEFAULTS.get(key)
            if key not in DEFAULTS or self._same_type(value, default):
                valid[key] = value
            else:
                self.load_warnings.append(
                    f'{self.path.name} has an invalid "{key}" value ({value!r}); '
                    f'expected a {type(default).__name__}, using the default ({default!r}).'
                )
        return valid

    @staticmethod
    def _same_type(value, default):
        if isinstance(default, bool):
            return isinstance(value, bool)
        if isinstance(default, (int, float)):
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        return isinstance(value, type(default))

    def _load(self):
        if not self.path.exists():
            return {}
        try:
            # utf-8-sig: tolerate the BOM PowerShell's Out-File -Encoding utf8
            # prepends, which plain utf-8 rejects as invalid JSON.
            with open(self.path, "r", encoding="utf-8-sig") as f:
                loaded = json.load(f)
        except json.JSONDecodeError as error:
            self.load_warnings.append(f"{self.path.name} is not valid JSON ({error}); using defaults.")
            return {}
        except UnicodeDecodeError as error:
            self.load_warnings.append(
                f"{self.path.name} is not UTF-8 encoded ({error}); using defaults. "
                f"(Was it saved as UTF-16? PowerShell's Out-File does that by default.)"
            )
            return {}
        except OSError as error:
            self.load_warnings.append(f"{self.path.name} could not be read ({error}); using defaults.")
            return {}
        if not isinstance(loaded, dict):
            self.load_warnings.append(f"{self.path.name} does not contain a JSON object; using defaults.")
            return {}
        return loaded
