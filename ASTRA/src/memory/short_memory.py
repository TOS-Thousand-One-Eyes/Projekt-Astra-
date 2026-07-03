class ShortMemory:

    def __init__(self):
        self.entries = []

    def remember(self, entry):
        self.entries.append(entry)

    def recall(self):
        return self.entries

    def forget(self, entry_text):
        target = entry_text.lower()
        before = len(self.entries)
        self.entries = [item for item in self.entries if item.lower() != target]
        return before - len(self.entries)