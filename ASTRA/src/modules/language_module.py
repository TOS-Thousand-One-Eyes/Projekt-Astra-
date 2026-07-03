import urllib.error

from modules.module import Module


class LanguageModule(Module):

    name = "language"

    def __init__(self, client, logger=None):
        self.client = client
        self.logger = logger
        self.available = False

    def start(self):
        self.available = False
        try:
            self.client.ensure_available()
        except urllib.error.HTTPError as error:
            raise ConnectionError(f"Ollama responded with an error (HTTP {error.code}).") from error
        except OSError as error:
            raise ConnectionError("Ollama not reachable.") from error
        self.available = True

    def stop(self):
        self.available = False

    def respond(self, message):
        if not self.available:
            return None

        try:
            return self.client.generate(message)
        except Exception as error:
            self.available = False
            if self.logger:
                self.logger.warning(
                    f"Local language model failed ({error}); falling back to the default "
                    "echo for the rest of this session."
                )
            return None
