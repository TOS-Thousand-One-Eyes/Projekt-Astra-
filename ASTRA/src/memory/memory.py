class Memory:
    def __init__(self,):
        self.memories = ["startup complete"]
    def remember(self, memory):
        self.memories.append(memory)
    def recall(self,):
        return self.memories
