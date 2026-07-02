import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_FILE = DATA_DIR / "long_memory.json"


class LongMemory:

    def __init__(self):
        self.entries = []
        self.load()

    def remember(self, entry):
        self.entries.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "entry": entry,
        })
        self.save()

    def recall(self):
        return self.entries

    def save(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, indent=2, ensure_ascii=False)

    def load(self):
        if not DATA_FILE.exists():
            self.entries = []
            return
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            self.entries = json.load(f)
