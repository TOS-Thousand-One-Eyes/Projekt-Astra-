
class Brain:
    def __init__(self, logger, config, memory):
        self.running = False
        self.logger = logger
        self.config = config
        self.memory = memory
    def start(self,):
        self.running = True
        self.greet()
        self.system_check()
        self.ready()
    def greet(self):
        self.logger.log(f"{self.config.name} v{self.config.version} is starting... (Running: {self.running})")
        self.logger.log(f"Hello! I am {self.config.name}")
    def system_check(self):
       pass
    def ready(self):
        pass