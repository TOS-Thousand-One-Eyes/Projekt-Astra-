import sys
import types

from PIL import Image

from vision.screen_observer import (
    ScreenObserverModule,
    _apply_actionability_filter,
    capture_screen,
)


class LoggerStub:
    def __init__(self):
        self.events = []

    def chat(self, message):
        self.events.append(("CHAT", message))

    def warning(self, message):
        self.events.append(("WARNING", message))

    def info(self, message):
        self.events.append(("INFO", message))

    def debug(self, message):
        self.events.append(("DEBUG", message))


class Client:
    model = "gemma3:4b"
    busy = False

    def ensure_available(self):
        return None

    def capabilities(self, *_args):
        return ["completion", "vision"]

    def generate_with_image_bytes(self, *_args, **_kwargs):
        return "unused"


class Describer:
    client = Client()

    def __init__(self, response):
        self.response = response

    def describe_bytes(self, *_args, **_kwargs):
        return {"description": self.response}


def fake_capture():
    return {
        "jpeg": b"JPEG",
        "proxy": Image.new("L", (160, 90), 0),
        "width": 100,
        "height": 100,
    }


def test_normal_greyed_ui_false_positive_is_suppressed():
    result = _apply_actionability_filter(
        {
            "noteworthy": True,
            "notify": True,
            "learning_worthy": True,
            "confidence": 0.99,
            "category": "other",
            "observation": "The Ollama ready status is greyed out.",
            "message": "The status is greyed out.",
        }
    )
    assert result["noteworthy"] is False
    assert result["notify"] is False


def test_real_error_remains_actionable():
    result = _apply_actionability_filter(
        {
            "noteworthy": True,
            "notify": True,
            "learning_worthy": False,
            "confidence": 0.95,
            "category": "error",
            "observation": "Python traceback",
            "message": "Run failed",
        }
    )
    assert result["noteworthy"] is True
    assert result["notify"] is True


def test_notification_prefers_event_callback_over_direct_logger_chat():
    logger = LoggerStub()
    events = []
    response = (
        '{"noteworthy":true,"notify":true,"learning_worthy":false,'
        '"confidence":0.99,"category":"error","observation":"traceback",'
        '"message":"Run failed"}'
    )
    observer = ScreenObserverModule(
        Describer(response),
        logger=logger,
        capture_func=fake_capture,
        foreground_func=lambda: {"process": "Code.exe", "title": "x", "pid": 1},
        lock_check=lambda: False,
        event_callback=events.append,
        notification_cooldown=0,
    )
    observer.analyze_once()
    assert len(events) == 1
    assert events[0]["type"] == "visual_observation"
    assert not any(level == "CHAT" for level, _ in logger.events)


def test_callback_failure_is_visible_and_falls_back_to_chat():
    logger = LoggerStub()
    response = (
        '{"noteworthy":true,"notify":true,"learning_worthy":false,'
        '"confidence":0.99,"category":"error","observation":"traceback",'
        '"message":"Run failed"}'
    )

    def broken(_event):
        raise RuntimeError("callback failure")

    observer = ScreenObserverModule(
        Describer(response),
        logger=logger,
        capture_func=fake_capture,
        foreground_func=lambda: {"process": "Code.exe", "title": "x", "pid": 1},
        lock_check=lambda: False,
        event_callback=broken,
        notification_cooldown=0,
    )
    observer.analyze_once()
    assert any(level == "WARNING" for level, _ in logger.events)
    assert any(level == "CHAT" for level, _ in logger.events)


def test_capture_screen_uses_primary_monitor_not_all_monitors(monkeypatch):
    chosen = []

    class Raw:
        size = (2, 2)
        rgb = b"\x00\x00\x00" * 4

    class FakeMSS:
        monitors = [{"all": True}, {"primary": True}, {"secondary": True}]

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def grab(self, monitor):
            chosen.append(monitor)
            return Raw()

    monkeypatch.setitem(sys.modules, "mss", types.SimpleNamespace(mss=lambda: FakeMSS()))
    result = capture_screen()
    assert chosen == [{"primary": True}]
    assert result["jpeg"]


def test_callback_can_decline_delivery_and_fall_back_to_chat():
    logger = LoggerStub()
    response = (
        '{"noteworthy":true,"notify":true,"learning_worthy":false,'
        '"confidence":0.99,"category":"error","observation":"traceback",'
        '"message":"Run failed"}'
    )
    observer = ScreenObserverModule(
        Describer(response),
        logger=logger,
        capture_func=fake_capture,
        foreground_func=lambda: {"process": "Code.exe", "title": "x", "pid": 1},
        lock_check=lambda: False,
        event_callback=lambda _event: False,
        notification_cooldown=0,
    )
    observer.analyze_once()
    assert any(level == "CHAT" for level, _ in logger.events)
