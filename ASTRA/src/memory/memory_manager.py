from memory.short_memory import ShortMemory
from memory.long_memory import LongMemory


class MemoryManager:

    def __init__(self):
        self.short_memory = ShortMemory()
        self.long_memory = LongMemory()

    def remember(self, entry):
        self.short_memory.remember(entry)

    def recall(self):
        return self.short_memory.recall()

    def clear(self):
        self.short_memory.clear()