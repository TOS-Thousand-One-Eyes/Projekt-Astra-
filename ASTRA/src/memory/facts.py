import json
import os
import threading
from pathlib import Path

from utils.file_store import atomic_json_write, interprocess_file_lock

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_FILE = DATA_DIR / "facts.json"


class Facts:

    def __init__(self, path=DATA_FILE):
        self.path = Path(path)
        self.facts = {}
        self.load_warning = None
        self._lock = threading.RLock()
        self.load()

    def learn(self, key, value):
        clean_key = key.strip().lower()
        clean_value = value.strip()
        with self._lock, interprocess_file_lock(self.path):
            facts = self._read_for_write()
            facts[clean_key] = clean_value
            self._write(facts)
            self.facts = facts

    def get(self, key):
        with self._lock:
            return self.facts.get(key.strip().lower())

    def all(self):
        with self._lock:
            return dict(self.facts)

    def save(self):
        with self._lock, interprocess_file_lock(self.path):
            # A malformed target may still be recoverable. Never replace it
            # merely because this instance fell back to an empty dictionary.
            self._read_for_write()
            self._write(self.facts)

    def load(self):
        with self._lock, interprocess_file_lock(self.path):
            try:
                self.facts = self._read()
            except (json.JSONDecodeError, UnicodeDecodeError, OSError, ValueError) as error:
                self.facts = {}
                self.load_warning = (
                    f"{self.path.name} could not be loaded ({error}); "
                    "starting with empty facts in read-only recovery mode."
                )

    def _read(self):
        if not self.path.exists():
            return {}
        # utf-8-sig: a hand-edited file saved with a BOM must not reset the
        # user's facts to empty.
        with open(self.path, "r", encoding="utf-8-sig") as handle:
            loaded = json.load(handle)
        if not isinstance(loaded, dict):
            raise ValueError("expected a JSON object")
        return self._normalized_keys(loaded)

    def _read_for_write(self):
        try:
            return self._read()
        except (json.JSONDecodeError, UnicodeDecodeError, OSError, ValueError) as error:
            raise OSError(
                f"Refusing to overwrite unreadable {self.path.name}: {error}"
            ) from error

    def _write(self, facts):
        atomic_json_write(self.path, facts, replace_func=os.replace)

    def _normalized_keys(self, loaded):
        # learn() stores keys stripped and lowercased and get() looks them up
        # the same way - a hand-edited key like "Name" would be listed by the
        # facts summary but unreachable by every lookup. Normalize on load,
        # and say so, since it changes what the user wrote.
        normalized = {}
        renamed = []
        overwritten = []
        for key, value in loaded.items():
            clean = key.strip().lower()
            if clean != key:
                renamed.append(key)
            if clean in normalized:
                overwritten.append(clean)
            normalized[clean] = value
        if renamed:
            self.load_warning = (
                f"{self.path.name} had keys in a different form than Astra stores them "
                f"({', '.join(repr(key) for key in renamed)}); normalized them on load so lookups find them."
            )
            if overwritten:
                self.load_warning += (
                    f" Two keys normalized to the same name "
                    f"({', '.join(repr(key) for key in overwritten)}); the value later in the file won."
                )
        return normalized
