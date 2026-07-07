import pytest
import subprocess

from commands.registry import build_default_registry
from commands.speech_command import SpeechCommand
from commands.vision_command import VisionCommand
from memory.memory_manager import MemoryManager
from speech.speech_manager import SpeechError, SpeechManager
from vision.image_inspector import ImageInspectionError, ImageInspector
from vision.semantic_vision import LocalVisionDescriber, VisionDescriptionError


def png_bytes(width=2, height=3):
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
        + b"\x00\x00\x00\x00"
    )


def test_speech_manager_invokes_windows_sapi_runner():
    calls = []

    def runner(args, check, capture_output, text, timeout):
        calls.append(
            {
                "args": args,
                "check": check,
                "capture_output": capture_output,
                "text": text,
                "timeout": timeout,
            }
        )

    manager = SpeechManager(runner=runner, system=lambda: "Windows")

    spoken = manager.speak(" hello   there ")

    assert spoken == "hello there"
    assert calls[0]["args"][0] == "powershell"
    assert calls[0]["args"][-1] == "hello there"
    assert calls[0]["check"] is True
    assert calls[0]["timeout"] == 20


def test_speech_manager_reports_unsupported_platform():
    manager = SpeechManager(runner=lambda *args, **kwargs: None, system=lambda: "Linux")

    with pytest.raises(SpeechError, match="Windows SAPI"):
        manager.speak("hello")


def test_speech_manager_listens_once_with_explicit_timeout():
    calls = []

    def runner(args, check, capture_output, text, timeout):
        calls.append(
            {
                "args": args,
                "check": check,
                "capture_output": capture_output,
                "text": text,
                "timeout": timeout,
            }
        )
        return subprocess.CompletedProcess(args, 0, stdout=" System online \n", stderr="")

    manager = SpeechManager(runner=runner, system=lambda: "Windows")

    transcript = manager.listen_once(7)

    assert transcript == "System online"
    assert calls[0]["args"][0] == "powershell"
    assert calls[0]["args"][-1] == "7"
    assert "SpeechRecognitionEngine" in calls[0]["args"][3]
    assert calls[0]["check"] is True
    assert calls[0]["timeout"] == 12


def test_speech_manager_listen_clamps_timeout():
    def runner(args, check, capture_output, text, timeout):
        return subprocess.CompletedProcess(args, 0, stdout=args[-1], stderr="")

    manager = SpeechManager(runner=runner, system=lambda: "Windows")

    assert manager.listen_once(999) == "30"


def test_speech_manager_reports_speak_timeout_cleanly():
    def runner(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="powershell", timeout=kwargs["timeout"])

    manager = SpeechManager(runner=runner, system=lambda: "Windows", speak_timeout=3)

    with pytest.raises(SpeechError, match="timed out after 3s"):
        manager.speak("hello")


def test_speech_manager_reports_listen_timeout_cleanly():
    def runner(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="powershell", timeout=kwargs["timeout"])

    manager = SpeechManager(runner=runner, system=lambda: "Windows")

    with pytest.raises(SpeechError, match="recognition timed out after 4s"):
        manager.listen_once(4)


def test_speech_manager_reports_unsupported_recognition_platform():
    manager = SpeechManager(runner=lambda *args, **kwargs: None, system=lambda: "Linux")

    with pytest.raises(SpeechError, match="Speech recognition"):
        manager.listen_once()


def test_speech_command_uses_injected_speaker():
    class StubSpeech:
        def __init__(self):
            self.spoken = []

        def speak(self, text):
            self.spoken.append(text)
            return text

    speech = StubSpeech()
    command = SpeechCommand(speech=speech)

    response = command.handle("speak System online", "speak system online")

    assert response == "Spoken: System online"
    assert speech.spoken == ["System online"]


def test_speech_command_uses_injected_listener_and_reports_status():
    class StubSpeech:
        def listen_once(self, seconds=5):
            assert seconds == "9"
            return "run diagnostics"

        def status(self):
            return {
                "platform": "Windows",
                "text_to_speech": True,
                "speech_to_text": True,
                "passive_listening": False,
            }

    command = SpeechCommand(speech=StubSpeech())

    assert command.handle("listen 9", "listen 9") == "Heard: run diagnostics"
    status = command.handle("speech status", "speech status")
    assert "speech-to-text: true" in status
    assert "passive listening: false" in status


def test_image_inspector_reads_png_dimensions(tmp_path):
    path = tmp_path / "sample.png"
    path.write_bytes(png_bytes(width=7, height=5))

    info = ImageInspector().inspect(path)

    assert info["format"] == "PNG"
    assert info["width"] == 7
    assert info["height"] == 5
    assert info["bytes"] == len(path.read_bytes())


def test_image_inspector_rejects_unknown_file(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("not an image", encoding="utf-8")

    with pytest.raises(ImageInspectionError, match="Unsupported"):
        ImageInspector().inspect(path)


def test_vision_command_formats_image_metadata(tmp_path):
    path = tmp_path / "sample.png"
    path.write_bytes(png_bytes(width=4, height=6))
    command = VisionCommand()

    response = command.handle(f"image inspect {path}", f"image inspect {path}".lower())

    assert "format: PNG" in response
    assert "size: 4x6" in response


def test_vision_command_reports_unconfigured_model_status():
    command = VisionCommand()

    status = command.handle("vision status", "vision status")
    check = command.handle("vision check", "vision check")

    assert "Vision model status:" in status
    assert "- configured: false" in status
    assert "Vision model unavailable" in check


def test_vision_command_checks_injected_vision_client():
    class StubClient:
        base_url = "http://localhost:11434"
        model = "llava:test"

        def __init__(self):
            self.checked = 0

        def ensure_available(self):
            self.checked += 1

        def generate_with_images(self, prompt, image_paths):
            return "description"

    client = StubClient()
    command = VisionCommand(describer=LocalVisionDescriber(client=client, source="vision"))

    status = command.handle("vision status", "vision status")
    check = command.handle("vision check", "vision check")

    assert "- configured: true" in status
    assert "- source: vision" in status
    assert "- model: llava:test" in status
    assert check == "Vision model available: llava:test at http://localhost:11434 (source: vision)."
    assert client.checked == 1


def test_vision_command_reports_language_fallback_source():
    class StubClient:
        base_url = "http://localhost:11434"
        model = "qwen3:test"

        def ensure_available(self):
            return None

        def generate_with_images(self, prompt, image_paths):
            return "description"

    class StubLanguageModule:
        client = StubClient()

    command = VisionCommand(language_module=StubLanguageModule())

    status = command.handle("vision status", "vision status")
    check = command.handle("vision check", "vision check")

    assert "- configured: true" in status
    assert "- source: language" in status
    assert "- model: qwen3:test" in status
    assert "Vision fallback client available: qwen3:test" in check
    assert "not a dedicated vision model" in check


def test_local_vision_describer_uses_client_with_image_payload(tmp_path):
    path = tmp_path / "sample.png"
    path.write_bytes(png_bytes(width=4, height=6))

    class StubClient:
        def __init__(self):
            self.calls = []

        def generate_with_images(self, prompt, image_paths):
            self.calls.append((prompt, image_paths))
            return "The image appears to be a small test PNG."

    client = StubClient()
    describer = LocalVisionDescriber(client=client)

    result = describer.describe(path, prompt="What is visible?")

    assert result["description"] == "The image appears to be a small test PNG."
    assert result["width"] == 4
    assert result["height"] == 6
    assert client.calls[0][1] == [str(path)]
    assert "What is visible?" in client.calls[0][0]


def test_local_vision_describer_requires_vision_client(tmp_path):
    path = tmp_path / "sample.png"
    path.write_bytes(png_bytes())

    with pytest.raises(VisionDescriptionError, match="vision-capable"):
        LocalVisionDescriber().describe(path)


def test_vision_command_describes_image_with_injected_describer(tmp_path):
    path = tmp_path / "sample.png"
    path.write_bytes(png_bytes(width=8, height=9))

    class StubDescriber:
        def describe(self, image_path, prompt=None):
            assert image_path == str(path)
            assert prompt == "What is here?"
            return {
                "path": str(path),
                "format": "PNG",
                "width": 8,
                "height": 9,
                "bytes": len(path.read_bytes()),
                "prompt": prompt,
                "description": "A generated test image.",
            }

    command = VisionCommand(describer=StubDescriber())

    response = command.handle(
        f"image describe {path} -- What is here?",
        f"image describe {path} -- what is here?".lower(),
    )

    assert "Image description:" in response
    assert "size: 8x9" in response
    assert "A generated test image." in response


def test_default_registry_dispatches_speech_and_vision_with_injected_adapters(tmp_path, config):
    class StubSpeech:
        def speak(self, text):
            return text

        def listen_once(self, seconds=5):
            return "voice command"

        def status(self):
            return {
                "platform": "test",
                "text_to_speech": True,
                "speech_to_text": True,
                "passive_listening": False,
            }

    class StubVision:
        def inspect(self, path):
            return {"path": path, "format": "PNG", "width": 1, "height": 2, "bytes": 3}

    class StubDescriber:
        def describe(self, image_path, prompt=None):
            return {
                "path": image_path,
                "format": "PNG",
                "width": 1,
                "height": 2,
                "bytes": 3,
                "prompt": prompt or "Describe the image.",
                "description": "A described image.",
            }

    memory = MemoryManager(data_dir=tmp_path / "memory")
    registry = build_default_registry(
        config,
        memory,
        speech=StubSpeech(),
        vision=StubVision(),
        vision_describer=StubDescriber(),
    )

    assert registry.dispatch("speak Online").response == "Spoken: Online"
    assert registry.dispatch("voice input").response == "Heard: voice command"
    assert "size: 1x2" in registry.dispatch("image inspect sample.png").response
    assert "A described image." in registry.dispatch("image describe sample.png").response
