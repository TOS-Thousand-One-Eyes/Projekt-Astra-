class ShortMemory:

    def __init__(self):
        self.entries = []

    def remember(self, entry):
        self.entries.append(entry)

    def recall(self):
        return self.entries

    def clear(self):
        self.entries.clear()