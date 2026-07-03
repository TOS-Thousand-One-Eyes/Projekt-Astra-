from pathlib import Path

from memory.short_memory import ShortMemory
from memory.long_memory import LongMemory
from memory.facts import Facts

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class MemoryManager:

    def __init__(self, data_dir=DATA_DIR):
        data_dir = Path(data_dir)
        self.short_memory = ShortMemory()
        self.long_memory = LongMemory(data_dir / "long_memory.json")
        self.facts = Facts(data_dir / "facts.json")

    def remember(self, entry, entry_type="chat"):
        self.short_memory.remember(entry)
        self.long_memory.remember(entry, entry_type=entry_type)

    def recall(self):
        return self.short_memory.recall()

    def recall_long(self):
        return self.long_memory.recall()

    def search_long(self, query):
        return self.long_memory.search(query)

    def forget(self, entry):
        removed = self.long_memory.forget(entry, entry_type="note")
        self.short_memory.forget(entry)
        return removed

    def learn(self, key, value):
        self.facts.learn(key, value)

    def get_fact(self, key):
        return self.facts.get(key)

    def all_facts(self):
        return self.facts.all()

    def load_warnings(self):
        return [warning for warning in (self.long_memory.load_warning, self.facts.load_warning) if warning]
