import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_FILE = DATA_DIR / "facts.json"


class Facts:

    def __init__(self, path=DATA_FILE):
        self.path = Path(path)
        self.facts = {}
        self.load()

    def learn(self, key, value):
        self.facts[key.strip().lower()] = value.strip()
        self.save()

    def get(self, key):
        return self.facts.get(key.strip().lower())

    def all(self):
        return self.facts

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.facts, f, indent=2, ensure_ascii=False)

    def load(self):
        if not self.path.exists():
            self.facts = {}
            return
        with open(self.path, "r", encoding="utf-8") as f:
            self.facts = json.load(f)
