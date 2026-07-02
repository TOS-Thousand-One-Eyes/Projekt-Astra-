class Brain:
    def __init__(self, logger):
        self.name = "Astra"
        self.version = "0.0.1"
        self.running = False
        self.logger = logger

    def start(self):
        self.running = True
        self.greet()
    def greet(self):
        self.logger.log(f"{self.name} v{self.version} is starting... (Running: {self.running})")
        self.logger.log(f"Hello! I am {self.name}")