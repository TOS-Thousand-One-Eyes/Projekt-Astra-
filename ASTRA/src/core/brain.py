from datetime import datetime

from commands.registry import build_default_registry
from utils.time_format import format_duration


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
        self.commands = commands or build_default_registry(
            config,
            memory,
            language_module=self._language_module(),
        )
        self.update_checker = update_checker
        self._session_started_at = None
        self._facts_at_start = 0
        self._messages_at_start = 0

    @property
    def is_running(self):
        return self.state == self.RUNNING

    def start(self):
        self._set_state(self.STARTING)
        self._session_started_at = datetime.now()
        self._facts_at_start = len(self.memory.all_facts())
        self._messages_at_start = len(self.memory.recall())
        long_entries = self.memory.recall_long()

        self.logger.log(f"{self.config.name} v{self.config.version} is starting...")
        self.logger.log(f"Config loaded from {self.config.path.name}.")
        self.logger.log(
            f"Memory loaded: {len(long_entries)} entries, "
            f"{self._facts_at_start} facts."
        )
        self.logger.log(f"Current time: {self._session_started_at.strftime('%Y-%m-%d %H:%M:%S')}.")
        self._log_last_seen(long_entries)
        self.modules.start_all()
        self.logger.log(f"Modules started: {len(self.modules.list_modules())}.")
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
        self.modules.stop_all()
        self.logger.log(f"Modules stopped: {len(self.modules.list_modules())}.")
        self._log_session_summary()
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

    def _log_last_seen(self, long_entries):
        if not long_entries:
            self.logger.log("This is our first session!")
            return
        last_timestamp = datetime.fromisoformat(long_entries[-1]["timestamp"])
        ago = format_duration(self._session_started_at - last_timestamp)
        self.logger.log(f"Last seen {ago} ago.")

    def _log_session_summary(self):
        message_count = len(self.memory.recall()) - self._messages_at_start
        new_facts = len(self.memory.all_facts()) - self._facts_at_start
        duration = format_duration(datetime.now() - self._session_started_at)
        self.logger.log(
            f"Session summary: {message_count} messages exchanged, "
            f"{new_facts} new facts learned, session lasted {duration}."
        )

    def _language_module(self):
        for module in self.modules.list_modules():
            if getattr(module, "name", None) == "language":
                return module
        return None

    def _set_state(self, new_state):
        allowed = self.TRANSITIONS[self.state]
        if new_state not in allowed:
            raise ValueError(f"Invalid state transition: {self.state} -> {new_state}")
        self.logger.log(f"State: {self.state} -> {new_state}")
        self.state = new_state
