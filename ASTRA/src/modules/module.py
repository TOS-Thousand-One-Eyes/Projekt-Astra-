class Module:
    """Base class for a Brain-managed subsystem (voice, vision, internet, ...)."""

    name = "module"

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError
