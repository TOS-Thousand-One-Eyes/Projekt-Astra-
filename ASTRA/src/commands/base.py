class Command:
    """Base class for a single chat command Brain can dispatch to."""

    help_text = None
    stops_brain = False

    def __init__(self, logger=None):
        self.logger = logger

    def handle(self, message, normalized):
        raise NotImplementedError

    def warn(self, message):
        """Log an observable-fallback warning if a logger was injected."""
        if self.logger:
            self.logger.warning(message)


class DispatchResult:

    def __init__(self, response, stops_brain=False):
        self.response = response
        self.stops_brain = stops_brain


def normalize(message):
    # Strip whitespace along with the punctuation: "bye !" must normalize
    # to "bye", not "bye ", or every exact-trigger match misses it.
    return message.strip().lower().rstrip("?!. \t\r\n")


def looks_like_shell_command(message):
    """True for stray shell invocations (e.g. a launch command pasted into the chat prompt)."""
    stripped = message.strip().lower()
    return ".exe" in stripped and stripped.endswith(".py")
