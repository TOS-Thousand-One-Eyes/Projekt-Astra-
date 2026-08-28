import json
import os
import re
import threading
import uuid
from pathlib import Path

from utils.logger import LEVELS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config.json"

UNKNOWN_VERSION = "0.0.0-unknown"
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$")

DEFAULTS = {
    "name": "Astra",
    "log_level": "INFO",
    "log_to_file": False,
    "check_for_updates": True,
    "gui_theme": "dark",
    "identity_auto_lock_minutes": 15,

    "use_language_fallback": False,
    "language_base_url": "http://localhost:11434",
    "language_model": "gemma3:4b",
    "language_generate_timeout": 240,
    "language_num_ctx": 4096,
    "language_temperature": 0.35,
    "language_keep_alive": "10m",

    "use_vision_model": False,
    "vision_base_url": "http://localhost:11434",
    "vision_model": "gemma3:4b",
    "vision_generate_timeout": 240,
    "vision_num_ctx": 2048,

    "self_learning_mode": "review",

    "screen_observer_enabled": False,
    "screen_observer_poll_seconds": 3,
    "screen_observer_min_analysis_interval": 90,
    "screen_observer_change_threshold": 0.06,
    "screen_observer_notify_threshold": 0.82,
    "screen_observer_notification_cooldown": 600,
}

_ALLOWED_SELF_LEARNING_MODES = {"off", "review", "auto"}
_ALLOWED_GUI_THEMES = {"dark", "light"}
_CONFIG_WRITE_LOCK = threading.RLock()
_PERSISTABLE_KEYS = set(DEFAULTS) | {"version"}


class Config:

    def __init__(self, path=CONFIG_FILE):
        self.path = Path(path)
        self.load_warnings = []
        settings = dict(DEFAULTS)
        settings.update(self._validated(self._load()))

        self.name = settings["name"]
        configured_version = settings.get("version")
        self.version = (
            configured_version.strip()
            if isinstance(configured_version, str)
            and VERSION_PATTERN.fullmatch(configured_version.strip())
            else UNKNOWN_VERSION
        )
        if self.version == UNKNOWN_VERSION:
            self.load_warnings.append(
                f'{self.path.name} has no valid "version" value; Astra can\'t tell '
                f"whether it's up to date until it's set (if update checks "
                f"are enabled, they still report the latest available version)."
            )

        self.log_level = self._validated_log_level(settings["log_level"])
        self.log_to_file = settings["log_to_file"]
        self.check_for_updates = settings["check_for_updates"]

        theme = str(settings["gui_theme"]).strip().lower()
        if theme not in _ALLOWED_GUI_THEMES:
            self.load_warnings.append(
                f'{self.path.name} has invalid "gui_theme" ({theme!r}); '
                'expected "dark" or "light". Using "dark".'
            )
            theme = "dark"
        self.gui_theme = theme
        self.identity_auto_lock_minutes = self._bounded_int(
            "identity_auto_lock_minutes",
            settings["identity_auto_lock_minutes"],
            minimum=0,
            maximum=1440,
        )

        self.use_language_fallback = settings["use_language_fallback"]
        self.language_base_url = settings["language_base_url"]
        self.language_model = settings["language_model"]
        self.language_generate_timeout = self._bounded_float(
            "language_generate_timeout",
            settings["language_generate_timeout"],
            minimum=1.0,
            maximum=3600.0,
        )
        self.language_num_ctx = self._bounded_int(
            "language_num_ctx", settings["language_num_ctx"], minimum=512, maximum=131072
        )
        self.language_temperature = self._bounded_float(
            "language_temperature", settings["language_temperature"], minimum=0.0, maximum=2.0
        )
        self.language_keep_alive = settings["language_keep_alive"]

        self.use_vision_model = settings["use_vision_model"]
        self.vision_base_url = settings["vision_base_url"]
        self.vision_model = settings["vision_model"]
        self.vision_generate_timeout = self._bounded_float(
            "vision_generate_timeout",
            settings["vision_generate_timeout"],
            minimum=1.0,
            maximum=3600.0,
        )
        self.vision_num_ctx = self._bounded_int(
            "vision_num_ctx", settings["vision_num_ctx"], minimum=512, maximum=131072
        )

        mode = str(settings["self_learning_mode"]).strip().lower()
        if mode not in _ALLOWED_SELF_LEARNING_MODES:
            self.load_warnings.append(
                f'{self.path.name} has invalid "self_learning_mode" ({mode!r}); '
                'expected "off", "review", or "auto". Using "review".'
            )
            mode = "review"
        self.self_learning_mode = mode

        self.screen_observer_enabled = settings["screen_observer_enabled"]
        self.screen_observer_poll_seconds = self._bounded_float(
            "screen_observer_poll_seconds",
            settings["screen_observer_poll_seconds"],
            minimum=1.0,
            maximum=3600.0,
        )
        self.screen_observer_min_analysis_interval = self._bounded_float(
            "screen_observer_min_analysis_interval",
            settings["screen_observer_min_analysis_interval"],
            minimum=10.0,
            maximum=86400.0,
        )
        self.screen_observer_change_threshold = self._bounded_float(
            "screen_observer_change_threshold",
            settings["screen_observer_change_threshold"],
            minimum=0.0,
            maximum=1.0,
        )
        self.screen_observer_notify_threshold = self._bounded_float(
            "screen_observer_notify_threshold",
            settings["screen_observer_notify_threshold"],
            minimum=0.0,
            maximum=1.0,
        )
        self.screen_observer_notification_cooldown = self._bounded_float(
            "screen_observer_notification_cooldown",
            settings["screen_observer_notification_cooldown"],
            minimum=0.0,
            maximum=86400.0,
        )

    def _validated_log_level(self, value):
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

    def _bounded_int(self, key, value, minimum, maximum):
        value = int(value)
        if minimum <= value <= maximum:
            return value
        fallback = int(DEFAULTS[key])
        self.load_warnings.append(
            f'{self.path.name} has out-of-range "{key}" ({value}); '
            f"expected {minimum}..{maximum}, using {fallback}."
        )
        return fallback

    def _bounded_float(self, key, value, minimum, maximum):
        value = float(value)
        if minimum <= value <= maximum:
            return value
        fallback = float(DEFAULTS[key])
        self.load_warnings.append(
            f'{self.path.name} has out-of-range "{key}" ({value}); '
            f"expected {minimum}..{maximum}, using {fallback}."
        )
        return fallback

    def persist(self, updates):
        """Atomically persist validated runtime settings and update this instance."""
        if not isinstance(updates, dict) or not updates:
            raise ValueError("Config updates must be a non-empty mapping.")

        normalized = {}
        for key, value in updates.items():
            if key not in _PERSISTABLE_KEYS:
                raise ValueError(f"Unknown persistent config setting: {key}")
            if key == "version":
                if (
                    not isinstance(value, str)
                    or not VERSION_PATTERN.fullmatch(value.strip())
                ):
                    raise ValueError(
                        "Config version must use numeric major.minor.patch format."
                    )
                normalized[key] = value.strip()
                continue

            default = DEFAULTS[key]
            if not self._same_type(value, default):
                raise ValueError(
                    f"Invalid value for {key}: expected {type(default).__name__}."
                )
            normalized[key] = value

        mode = normalized.get("self_learning_mode")
        if mode is not None and mode not in _ALLOWED_SELF_LEARNING_MODES:
            raise ValueError(
                "Invalid self_learning_mode; use off, review, or auto."
            )
        theme = normalized.get("gui_theme")
        if theme is not None and theme not in _ALLOWED_GUI_THEMES:
            raise ValueError("Invalid gui_theme; use dark or light.")

        tmp_path = None
        try:
            with _CONFIG_WRITE_LOCK:
                payload = {}
                if self.path.exists():
                    with open(self.path, "r", encoding="utf-8-sig") as handle:
                        loaded = json.load(handle)
                    if not isinstance(loaded, dict):
                        raise ValueError(
                            f"{self.path.name} does not contain a JSON object."
                        )
                    payload = loaded

                payload.update(normalized)
                self.path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = self.path.with_suffix(
                    f"{self.path.suffix}.{os.getpid()}.{threading.get_ident()}."
                    f"{uuid.uuid4().hex[:8]}.tmp"
                )
                with open(tmp_path, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2, ensure_ascii=False)
                    handle.write("\n")
                os.replace(tmp_path, self.path)
                tmp_path = None
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            warning = f"Failed to persist config settings ({error})."
            if warning not in self.load_warnings:
                self.load_warnings.append(warning)
            return False
        finally:
            if tmp_path is not None:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass

        for key, value in normalized.items():
            setattr(self, key, value)
        return True

    def _load(self):
        if not self.path.exists():
            return {}
        try:
            with open(self.path, "r", encoding="utf-8-sig") as f:
                loaded = json.load(f)
        except json.JSONDecodeError as error:
            self.load_warnings.append(
                f"{self.path.name} is not valid JSON ({error}); using defaults."
            )
            return {}
        except UnicodeDecodeError as error:
            self.load_warnings.append(
                f"{self.path.name} is not UTF-8 encoded ({error}); using defaults. "
                f"(Was it saved as UTF-16? PowerShell's Out-File does that by default.)"
            )
            return {}
        except OSError as error:
            self.load_warnings.append(
                f"{self.path.name} could not be read ({error}); using defaults."
            )
            return {}
        if not isinstance(loaded, dict):
            self.load_warnings.append(
                f"{self.path.name} does not contain a JSON object; using defaults."
            )
            return {}
        return loaded
