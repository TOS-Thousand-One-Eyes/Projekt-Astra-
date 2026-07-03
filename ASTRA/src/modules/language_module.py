from modules.module import Module


class LanguageModule(Module):

    name = "language"

    def __init__(self, client):
        self.client = client
        self.available = False

    def start(self):
        self.available = False
        try:
            self.client.ensure_available()
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
        except Exception:
            self.available = False
            return None
