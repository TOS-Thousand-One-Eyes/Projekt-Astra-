from datetime import datetime

from commands.registry import build_default_registry
from experience.experience_manager import ExperienceManager
from experience.reflection_manager import ReflectionManager
from utils.time_format import format_duration


class Brain:

    OFFLINE = "OFFLINE"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"

    TRANSITIONS = {
        OFFLINE: (STARTING,),
        STARTING: (RUNNING, OFFLINE),
        RUNNING: (STOPPING,),
        STOPPING: (OFFLINE,),
    }

    def __init__(
        self,
        logger,
        config,
        memory,
        modules,
        commands=None,
        update_checker=None,
        learning=None,
        actions=None,
        speech=None,
        vision=None,
        vision_describer=None,
        code=None,
        reminders=None,
        system_actions=None,
        experience=None,
        reflections=None,
        self_learning=None,
        screen_observer=None,
        identity=None,
        identity_manager=None,
    ):
        self.state = self.OFFLINE
        self.logger = logger
        self.config = config
        self.memory = memory
        self.modules = modules
        self.learning = learning
        self.self_learning = self_learning
        self.screen_observer = screen_observer
        self.identity = identity
        self.identity_manager = identity_manager
        self.experience = experience or ExperienceManager()
        self.reflections = reflections or ReflectionManager()
        self.commands = (
            commands
            if commands is not None
            else build_default_registry(
                config,
                memory,
                language_module=self._language_module(),
                learning=learning,
                self_learning=self_learning,
                actions=actions,
                speech=speech,
                vision=vision,
                vision_describer=vision_describer,
                screen_observer=screen_observer,
                code=code,
                reminders=reminders,
                system_actions=system_actions,
                experience=self.experience,
                reflections=self.reflections,
                logger=logger,
                identity=identity,
                identity_manager=identity_manager,
            )
        )
        self.update_checker = update_checker
        if self.screen_observer and callable(
            getattr(self.screen_observer, "set_event_callback", None)
        ):
            self.screen_observer.set_event_callback(self.receive_visual_event)
        self._session_started_at = None
        self._session_id = None
        self._facts_at_start = 0
        self._message_count = 0
        self._last_response = ""

    @property
    def is_running(self):
        return self.state == self.RUNNING

    def start(self):
        self._set_state(self.STARTING)
        try:
            self._session_started_at = datetime.now()
            self._session_id = self._session_started_at.strftime(
                "SESSION-%Y%m%d-%H%M%S"
            )
            self._facts_at_start = len(
                self.memory.all_facts()
            )
            self._message_count = 0
            self._last_response = ""
            long_entries = self.memory.recall_long()

            self.logger.log(
                f"{self.config.name} v{self.config.version} is starting..."
            )
            self.logger.log(
                f"Config loaded from {self.config.path.name}."
            )
            if self.identity:
                self.logger.log(
                    "Active profile: "
                    f"{self.identity.display_name} ({self.identity.user_id})."
                )
            for warning in self.config.load_warnings:
                self.logger.warning(warning)
            self.logger.log(
                f"Memory loaded: {len(long_entries)} entries, "
                f"{self._facts_at_start} facts."
            )
            for warning in self.memory.load_warnings():
                self.logger.warning(warning)
            for warning in getattr(
                self.experience, "load_warnings", []
            ):
                self.logger.warning(warning)
            for warning in getattr(
                self.reflections, "load_warnings", []
            ):
                self.logger.warning(warning)
            for manager in (self.learning, self.self_learning):
                for warning in getattr(manager, "load_warnings", []) if manager else []:
                    self.logger.warning(warning)
            self.logger.log(
                f"Current time: "
                f"{self._session_started_at.strftime('%Y-%m-%d %H:%M:%S')}."
            )
            self._log_last_seen(long_entries)
            self.modules.start_all()
            self.logger.log(
                f"Modules started: "
                f"{len(self.modules.list_modules())}."
            )
            self._set_state(self.RUNNING)
        except Exception as error:
            self._recover_to_offline(
                "Startup",
                error,
            )
            raise

        self.logger.log("Brain is ready.")
        name = (
            self.identity.display_name
            if self.identity
            else self.memory.get_fact("name")
        )
        if name:
            self.logger.log(
                f"Hello, {name}! I am {self.config.name}."
            )
        else:
            self.logger.log(
                f"Hello! I am {self.config.name}."
            )

        if self.update_checker:
            self.update_checker.check()

    def stop(self):
        self._set_state(self.STOPPING)
        try:
            self.logger.log(
                f"Stopping {self.config.name}..."
            )
            self.modules.stop_all()
            self.logger.log(
                f"Modules stopped: "
                f"{len(self.modules.list_modules())}."
            )
            self._log_session_summary()
        except Exception as error:
            self._recover_to_offline(
                "Shutdown",
                error,
            )
            raise
        self._set_state(self.OFFLINE)
        self.logger.log(
            f"{self.config.name} stopped."
        )

    def receive(self, message):
        if not self.is_running:
            return f"{self.config.name} is not running."

        if self.self_learning and callable(
            getattr(self.self_learning, "set_previous_assistant", None)
        ):
            self.self_learning.set_previous_assistant(self._last_response)

        result = self.commands.dispatch(message)

        try:
            self.memory.remember(message)
            self.memory.remember(result.response)
        except OSError as error:
            self.logger.error(
                f"Failed to save this exchange to long-term memory ({error}); "
                f"the conversation continues, but it may not persist."
            )

        try:
            self.experience.record_exchange(
                message,
                result.response,
                command_name=result.command_name,
                session_id=self._session_id,
                actor_id=(self.identity.user_id if self.identity else None),
            )
        except Exception as error:
            self.logger.error(
                f"Failed to save this exchange to structured experience memory "
                f"({error}); the conversation continues, but it may not be "
                "available for reflection."
            )

        self._last_response = result.response
        self._message_count += 2
        self.logger.chat(
            f"{self.config.name}: {result.response}"
        )

        if result.stops_brain:
            self.stop()

        return result.response

    def receive_visual_event(self, event):
        """Surface a user-facing Eyes event and record it in structured experience."""
        if not self.is_running or not isinstance(event, dict):
            return False
        message = " ".join(str(event.get("message") or "").split())[:500]
        observation = " ".join(str(event.get("observation") or "").split())[:500]
        if not message:
            return False

        try:
            self.experience.record_exchange(
                observation or "Visual observation",
                message,
                command_name="EyesObservation",
                session_id=self._session_id,
                source="eyes",
                actor_id=(self.identity.user_id if self.identity else None),
            )
        except Exception as error:
            self.logger.error(
                f"Failed to save Eyes event to structured experience memory ({error})."
            )

        self.logger.chat(f"{self.config.name}: {message}")
        return True

    def process(self, message):
        return self.commands.dispatch(message).response

    def _log_last_seen(self, long_entries):
        if not long_entries:
            self.logger.log(
                "This is our first session!"
            )
            return

        raw_timestamp = long_entries[-1].get(
            "timestamp"
        )
        try:
            last_timestamp = datetime.fromisoformat(
                raw_timestamp
            )
        except (TypeError, ValueError):
            self.logger.warning(
                "Couldn't read the newest long-term memory entry's timestamp "
                f"({raw_timestamp!r}); skipping the last-seen line."
            )
            return

        if last_timestamp.tzinfo is not None:
            last_timestamp = (
                last_timestamp.astimezone()
                .replace(tzinfo=None)
            )

        ago = format_duration(
            self._session_started_at
            - last_timestamp
        )
        self.logger.log(
            f"Last seen {ago} ago."
        )

    def _log_session_summary(self):
        new_facts = (
            len(self.memory.all_facts())
            - self._facts_at_start
        )
        duration = format_duration(
            datetime.now()
            - self._session_started_at
        )
        self.logger.log(
            f"Session summary: {self._message_count} messages exchanged, "
            f"{new_facts} new facts learned, session lasted {duration}."
        )

    def _language_module(self):
        for module in self.modules.list_modules():
            if getattr(
                module, "name", None
            ) == "language":
                return module
        return None

    def _recover_to_offline(
        self,
        phase,
        error,
    ):
        self.logger.error(
            f"{phase} failed mid-transition "
            f"({type(error).__name__}: {error}); "
            f"returning to {self.OFFLINE} so the brain can be started again."
        )
        self._set_state(self.OFFLINE)

    def _set_state(self, new_state):
        allowed = self.TRANSITIONS[
            self.state
        ]
        if new_state not in allowed:
            raise ValueError(
                f"Invalid state transition: "
                f"{self.state} -> {new_state}"
            )
        self.logger.log(
            f"State: {self.state} -> {new_state}"
        )
        self.state = new_state
