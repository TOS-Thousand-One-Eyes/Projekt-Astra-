import json
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_FILE = DATA_DIR / "long_memory.json"


class LongMemory:

    def __init__(self, path=DATA_FILE):
        self.path = Path(path)
        self.entries = []
        self.load_warning = None
        self.load()

    def remember(self, entry, entry_type="chat"):
        self.entries.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "entry": entry,
            "type": entry_type,
        })
        self.save()

    def recall(self):
        return self.entries

    def search(self, query):
        query_lower = query.lower()
        return [item for item in self.entries if query_lower in str(item.get("entry", "")).lower()]

    def forget(self, entry_text, entry_type=None):
        target = entry_text.lower()

        def matches(item):
            same_text = str(item.get("entry", "")).lower() == target
            same_type = entry_type is None or item.get("type") == entry_type
            return same_text and same_type

        before = len(self.entries)
        self.entries = [item for item in self.entries if not matches(item)]
        removed = before - len(self.entries)
        if removed:
            self.save()
        return removed

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self.path)

    def load(self):
        if not self.path.exists():
            self.entries = []
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except (json.JSONDecodeError, OSError) as error:
            self.entries = []
            self.load_warning = f"{self.path.name} could not be loaded ({error}); starting with empty long-term memory."
            return
        if not isinstance(loaded, list) or not all(isinstance(item, dict) for item in loaded):
            self.entries = []
            self.load_warning = f"{self.path.name} does not contain a JSON list of entries; starting with empty long-term memory."
            return
        self.entries = loaded
