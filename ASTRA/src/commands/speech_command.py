from commands.base import Command
from speech.speech_manager import SpeechError, SpeechManager


class SpeechCommand(Command):
    help_text = (
        "- speak <text> - read text aloud with the local speech engine\n"
        "- listen [seconds] / speech listen [seconds] - explicitly transcribe one microphone utterance\n"
        "- speech status - show local speech adapter capabilities"
    )

    def __init__(self, speech=None, logger=None):
        super().__init__(logger)
        self.speech = speech or SpeechManager()

    def handle(self, message, normalized):
        if normalized == "speech status":
            return self._status()
        if normalized == "listen":
            return self._listen()
        if normalized.startswith("listen "):
            return self._listen(message.strip()[len("listen "):])
        if normalized == "speech listen":
            return self._listen()
        if normalized.startswith("speech listen "):
            return self._listen(message.strip()[len("speech listen "):])
        if normalized == "voice input":
            return self._listen()
        if normalized.startswith("voice input "):
            return self._listen(message.strip()[len("voice input "):])
        if normalized.startswith("speak "):
            return self._speak(message.strip()[len("speak "):])
        if normalized.startswith("say "):
            return self._speak(message.strip()[len("say "):])
        return None

    def _speak(self, text):
        try:
            spoken = self.speech.speak(text)
        except ValueError as error:
            return str(error)
        except SpeechError as error:
            return str(error)
        return f"Spoken: {spoken}"

    def _listen(self, seconds=5):
        try:
            transcript = self.speech.listen_once(seconds)
        except ValueError as error:
            return str(error)
        except SpeechError as error:
            return str(error)
        return f"Heard: {transcript}"

    def _status(self):
        status = self.speech.status()
        return (
            "Speech status:\n"
            f"- platform: {status['platform']}\n"
            f"- text-to-speech: {str(status['text_to_speech']).lower()}\n"
            f"- speech-to-text: {str(status['speech_to_text']).lower()}\n"
            f"- passive listening: {str(status['passive_listening']).lower()}"
        )
