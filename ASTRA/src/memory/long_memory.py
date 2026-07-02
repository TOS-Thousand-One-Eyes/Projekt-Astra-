import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_FILE = DATA_DIR / "long_memory.json"


class LongMemory:

    def __init__(self, path=DATA_FILE):
        self.path = Path(path)
        self.entries = []
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
        return [item for item in self.entries if query_lower in item["entry"].lower()]

    def forget(self, entry_text):
        before = len(self.entries)
        self.entries = [item for item in self.entries if item["entry"] != entry_text]
        removed = before - len(self.entries)
        if removed:
            self.save()
        return removed

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, indent=2, ensure_ascii=False)

    def load(self):
        if not self.path.exists():
            self.entries = []
            return
        with open(self.path, "r", encoding="utf-8") as f:
            self.entries = json.load(f)
