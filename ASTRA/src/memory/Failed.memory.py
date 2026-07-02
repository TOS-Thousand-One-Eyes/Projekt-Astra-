import json

class Memory:
    def __init__(self,):
        self.memories = []
        self.load()
    def remember(self, memory):
        self.memories.append(memory)
        self.save()
    def save(self,):
        with open("data/memory.json", "w") as f:
            json.dump(self.memories, f)
    def load(self,):
        with open("data/memory.json", "r") as f:
            self.memories = json.load(f)
    def recall(self,):
        return self.memories
