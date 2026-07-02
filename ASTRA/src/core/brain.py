
class Brain:

    def __init__(self, logger, config, memory, modules):
        self.state = "OFFLINE"
        self.logger = logger
        self.config = config
        self.memory = memory
        self.modules = modules
        
    def start(self):
        self.state = "STARTING"
        self.greet()
        self.system_check()
        self.ready()
        self.state = "RUNNING"
    
    def greet(self):
        self.logger.log(f"{self.config.name} v{self.config.version} is starting...")
        self.logger.log(f"Current state: {self.state}")
        self.logger.log(f"Hello! I am {self.config.name}")
    
    def system_check(self):
        pass
    
    def ready(self):
        self.logger.log("Brain is ready.")

    def stop(self):
        self.state = "STOPPING"
        self.logger.log("Stopping Astra...")
        self.state = "OFFLINE"
        self.logger.log("Astra stopped.")

    def receive(self, message):
        self.memory.remember(message)
        
    