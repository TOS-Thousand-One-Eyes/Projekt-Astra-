from memory.short_memory import ShortMemory
from memory.long_memory import LongMemory
from memory.facts import Facts


class MemoryManager:

    def __init__(self):
        self.short_memory = ShortMemory()
        self.long_memory = LongMemory()
        self.facts = Facts()

    def remember(self, entry):
        self.short_memory.remember(entry)
        self.long_memory.remember(entry)

    def recall(self):
        return self.short_memory.recall()

    def recall_long(self):
        return self.long_memory.recall()

    def learn(self, key, value):
        self.facts.learn(key, value)

    def get_fact(self, key):
        return self.facts.get(key)

    def all_facts(self):
        return self.facts.all()

    def clear(self):
        self.short_memory.clear()
