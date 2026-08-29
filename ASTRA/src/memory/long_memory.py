import json
import os
import threading
from datetime import datetime
from pathlib import Path

from utils.file_store import atomic_json_write, interprocess_file_lock

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_FILE = DATA_DIR / "long_memory.json"


class LongMemory:

    def __init__(self, path=DATA_FILE):
        self.path = Path(path)
        self.entries = []
        self.load_warning = None
        self._lock = threading.RLock()
        self.load()

    def remember(self, entry, entry_type="chat"):
        with self._lock, interprocess_file_lock(self.path):
            entries = self._read_for_write()
            entries.append({
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "entry": entry,
                "type": entry_type,
            })
            self._write(entries)
            self.entries = entries

    def recall(self):
        with self._lock:
            return [dict(item) for item in self.entries]

    def search(self, query):
        query_lower = query.lower()
        with self._lock:
            return [
                dict(item)
                for item in self.entries
                if query_lower in str(item.get("entry", "")).lower()
            ]

    def forget(self, entry_text, entry_type=None):
        target = entry_text.lower()

        def matches(item):
            same_text = str(item.get("entry", "")).lower() == target
            same_type = entry_type is None or item.get("type") == entry_type
            return same_text and same_type

        with self._lock, interprocess_file_lock(self.path):
            entries = self._read_for_write()
            before = len(entries)
            remaining = [item for item in entries if not matches(item)]
            removed = before - len(remaining)
            if removed:
                self._write(remaining)
            self.entries = remaining
            return removed

    def save(self):
        with self._lock, interprocess_file_lock(self.path):
            # Validate the current target before replacing it. A corrupt store
            # may still contain recoverable user history and must not be erased.
            self._read_for_write()
            self._write(self.entries)

    def load(self):
        with self._lock, interprocess_file_lock(self.path):
            try:
                self.entries = self._read()
            except (json.JSONDecodeError, UnicodeDecodeError, OSError, ValueError) as error:
                self.entries = []
                self.load_warning = (
                    f"{self.path.name} could not be loaded ({error}); "
                    "starting with empty long-term memory in read-only recovery mode."
                )

    def _read(self):
        if not self.path.exists():
            return []
        # utf-8-sig: a hand-edited file saved with a BOM must not reset the
        # user's long-term memory to empty.
        with open(self.path, "r", encoding="utf-8-sig") as handle:
            loaded = json.load(handle)
        if not isinstance(loaded, list) or not all(
            isinstance(item, dict) for item in loaded
        ):
            raise ValueError("expected a JSON list of entry objects")
        return loaded

    def _read_for_write(self):
        try:
            return self._read()
        except (json.JSONDecodeError, UnicodeDecodeError, OSError, ValueError) as error:
            raise OSError(
                f"Refusing to overwrite unreadable {self.path.name}: {error}"
            ) from error

    def _write(self, entries):
        atomic_json_write(self.path, entries, replace_func=os.replace)
