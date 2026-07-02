class Memory:
    def __init__(self,):
        self.memories = ["Hello", "World"]
    def remember(self, memory):
        self.memories.append(memory)
    def recall(self,):
        return self.memories
