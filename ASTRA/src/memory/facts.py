import json
import os
import threading
import uuid
from pathlib import Path

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
        with self._lock:
            self.facts[key.strip().lower()] = value.strip()
            self.save()

    def get(self, key):
        with self._lock:
            return self.facts.get(key.strip().lower())

    def all(self):
        with self._lock:
            return dict(self.facts)

    def save(self):
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.path.with_suffix(
                f"{self.path.suffix}.{os.getpid()}.{threading.get_ident()}."
                f"{uuid.uuid4().hex[:8]}.tmp"
            )
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(self.facts, f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, self.path)
            finally:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def load(self):
        with self._lock:
            if not self.path.exists():
                self.facts = {}
                return
            try:
                # utf-8-sig: a hand-edited file saved with a BOM must not reset
                # the user's facts to empty.
                with open(self.path, "r", encoding="utf-8-sig") as f:
                    loaded = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError, OSError) as error:
                self.facts = {}
                self.load_warning = (
                    f"{self.path.name} could not be loaded ({error}); "
                    "starting with empty facts."
                )
                return
            if not isinstance(loaded, dict):
                self.facts = {}
                self.load_warning = (
                    f"{self.path.name} does not contain a JSON object; "
                    "starting with empty facts."
                )
                return
            self.facts = self._normalized_keys(loaded)

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
