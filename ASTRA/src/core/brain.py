from commands.registry import build_default_registry


class Brain:

    OFFLINE = "OFFLINE"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"

    TRANSITIONS = {
        OFFLINE: (STARTING,),
        STARTING: (RUNNING,),
        RUNNING: (STOPPING,),
        STOPPING: (OFFLINE,),
    }

    def __init__(self, logger, config, memory, modules, commands=None, update_checker=None):
        self.state = self.OFFLINE
        self.logger = logger
        self.config = config
        self.memory = memory
        self.modules = modules
        self.commands = commands or build_default_registry(config, memory)
        self.update_checker = update_checker

    @property
    def is_running(self):
        return self.state == self.RUNNING

    def start(self):
        self._set_state(self.STARTING)
        self.logger.log(f"{self.config.name} v{self.config.version} is starting...")
        self.logger.log(f"Config loaded from {self.config.path.name}.")
        self.logger.log(
            f"Memory loaded: {len(self.memory.recall_long())} entries, "
            f"{len(self.memory.all_facts())} facts."
        )
        self._set_state(self.RUNNING)
        self.logger.log("Brain is ready.")
        name = self.memory.get_fact("name")
        if name:
            self.logger.log(f"Hello, {name}! I am {self.config.name}.")
        else:
            self.logger.log(f"Hello! I am {self.config.name}.")

        if self.update_checker:
            self.update_checker.check()

    def stop(self):
        self._set_state(self.STOPPING)
        self.logger.log(f"Stopping {self.config.name}...")
        self._set_state(self.OFFLINE)
        self.logger.log(f"{self.config.name} stopped.")

    def receive(self, message):
        if not self.is_running:
            return f"{self.config.name} is not running."

        result = self.commands.dispatch(message)
        self.memory.remember(message)
        self.memory.remember(result.response)
        self.logger.log(f"You: {message}")
        self.logger.log(f"{self.config.name}: {result.response}")

        if result.stops_brain:
            self.stop()

        return result.response

    def process(self, message):
        return self.commands.dispatch(message).response

    def _set_state(self, new_state):
        allowed = self.TRANSITIONS[self.state]
        if new_state not in allowed:
            raise ValueError(f"Invalid state transition: {self.state} -> {new_state}")
        self.logger.log(f"State: {self.state} -> {new_state}")
        self.state = new_state
