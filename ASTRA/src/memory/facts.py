import json
import os
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_FILE = DATA_DIR / "facts.json"


class Facts:

    def __init__(self, path=DATA_FILE):
        self.path = Path(path)
        self.facts = {}
        self.load_warning = None
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
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.facts, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self.path)

    def load(self):
        if not self.path.exists():
            self.facts = {}
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except (json.JSONDecodeError, OSError) as error:
            self.facts = {}
            self.load_warning = f"{self.path.name} could not be loaded ({error}); starting with empty facts."
            return
        if not isinstance(loaded, dict):
            self.facts = {}
            self.load_warning = f"{self.path.name} does not contain a JSON object; starting with empty facts."
            return
        self.facts = loaded
