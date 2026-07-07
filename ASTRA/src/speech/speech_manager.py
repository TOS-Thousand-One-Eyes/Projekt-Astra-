import platform
import subprocess


class SpeechError(Exception):
    pass


class SpeechManager:
    """Small local speech adapter for explicit text-to-speech and speech-to-text."""

    def __init__(self, runner=None, system=None, speak_timeout=20, listen_timeout_grace=5):
        self.runner = runner or subprocess.run
        self.system = system or platform.system
        self.speak_timeout = max(1, int(speak_timeout))
        self.listen_timeout_grace = max(1, int(listen_timeout_grace))

    def speak(self, text):
        clean = " ".join(str(text).split())
        if not clean:
            raise ValueError("Speech text cannot be empty.")
        if self.system().lower() != "windows":
            raise SpeechError("Speech is currently implemented for Windows SAPI only.")
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$speaker.Speak($args[0])"
        )
        try:
            self.runner(
                ["powershell", "-NoProfile", "-Command", script, clean],
                check=True,
                capture_output=True,
                text=True,
                timeout=self.speak_timeout,
            )
        except subprocess.TimeoutExpired as error:
            raise SpeechError(f"Speech timed out after {self.speak_timeout}s.") from error
        except (OSError, subprocess.CalledProcessError) as error:
            raise SpeechError(f"Speech failed: {error}") from error
        return clean

    def listen_once(self, seconds=5):
        timeout = normalize_seconds(seconds)
        if self.system().lower() != "windows":
            raise SpeechError("Speech recognition is currently implemented for Windows System.Speech only.")
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$seconds = [double]$args[0]; "
            "$culture = [System.Globalization.CultureInfo]::CurrentCulture; "
            "$recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine($culture); "
            "$recognizer.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar)); "
            "$recognizer.SetInputToDefaultAudioDevice(); "
            "$result = $recognizer.Recognize([TimeSpan]::FromSeconds($seconds)); "
            "if ($result -and $result.Text) { Write-Output $result.Text } else { exit 2 }"
        )
        try:
            result = self.runner(
                ["powershell", "-NoProfile", "-Command", script, str(timeout)],
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout + self.listen_timeout_grace,
            )
        except subprocess.TimeoutExpired as error:
            raise SpeechError(f"Speech recognition timed out after {timeout}s.") from error
        except (OSError, subprocess.CalledProcessError) as error:
            raise SpeechError(f"Speech recognition failed: {error}") from error
        transcript = " ".join(str(getattr(result, "stdout", "")).split())
        if not transcript:
            raise SpeechError("No speech was recognized.")
        return transcript

    def status(self):
        is_windows = self.system().lower() == "windows"
        return {
            "platform": self.system(),
            "text_to_speech": is_windows,
            "speech_to_text": is_windows,
            "passive_listening": False,
        }


def normalize_seconds(value):
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        seconds = 5
    return max(1, min(seconds, 30))
