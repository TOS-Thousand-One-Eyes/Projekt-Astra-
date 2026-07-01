class Brain:
    def __init__(self):
        self.name = "Astra"
        self.version = "0.0.1"
        self.running = False

        print(f"{self.name} ver.{self.version} | running:{self.running} initialized")

    def greet(self):
        print(f"Hello, I am {self.name} ver.{self.version} | running:{self.running}.")
