class Command:
    """Base class for a single chat command Brain can dispatch to."""

    help_text = None
    stops_brain = False

    def handle(self, message, normalized):
        raise NotImplementedError


class DispatchResult:

    def __init__(self, response, stops_brain=False):
        self.response = response
        self.stops_brain = stops_brain


def normalize(message):
    return message.strip().lower().rstrip("?!.")


def looks_like_shell_command(message):
    """True for stray shell invocations (e.g. a launch command pasted into the chat prompt)."""
    stripped = message.strip().lower()
    return ".exe" in stripped and stripped.endswith(".py")
