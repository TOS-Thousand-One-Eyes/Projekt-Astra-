from types import SimpleNamespace

import gui.app as gui_app
from gui.app import AstraTkApp
from identity.identity_manager import IdentityStoreError


def test_restart_is_refused_while_an_old_model_refresh_is_running():
    app = AstraTkApp.__new__(AstraTkApp)
    app.worker_running = False
    app.model_refresh_running = True

    class BrainThatMustNotStop:
        is_running = True

        def stop(self):
            raise AssertionError("restart must not stop this runtime")

    app.brain = BrainThatMustNotStop()
    app._start_runtime = lambda: (_ for _ in ()).throw(
        AssertionError("restart must not start a second runtime")
    )

    app.restart_runtime()

    assert app.brain.is_running
    assert app.model_refresh_running is True


def test_model_refresh_is_not_started_for_a_stopped_brain():
    app = AstraTkApp.__new__(AstraTkApp)
    app.model_refresh_running = False
    app.brain = SimpleNamespace(is_running=False)
    app.model_refresh_button = SimpleNamespace(
        configure=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("stopped runtime must not touch refresh controls")
        )
    )

    app.refresh_models()

    assert app.model_refresh_running is False


def test_lock_switch_store_failure_closes_instead_of_reopening_old_profile(monkeypatch):
    app = AstraTkApp.__new__(AstraTkApp)
    app.worker_running = False
    app.model_refresh_running = False
    app.config = object()
    app.logger = object()
    app.brain = SimpleNamespace(is_running=True, stop=lambda: None)
    app.identity_manager = object()
    app.model_var = SimpleNamespace(set=lambda _value: None)
    app.model_combo = {}
    app._set_controls_enabled = lambda _enabled: None
    app._drain_events = lambda: None
    app._clear_chat = lambda: None
    app._start_runtime = lambda: (_ for _ in ()).throw(
        AssertionError("old profile must not restart after login failure")
    )

    class Root:
        def __init__(self):
            self.withdrawn = False
            self.deiconified = False
            self.destroyed = False

        def withdraw(self):
            self.withdrawn = True

        def deiconify(self):
            self.deiconified = True

        def destroy(self):
            self.destroyed = True

    app.root = Root()
    errors = []
    monkeypatch.setattr(
        gui_app,
        "prompt_gui_identity",
        lambda *_args: (_ for _ in ()).throw(IdentityStoreError("store unreadable")),
    )
    monkeypatch.setattr(
        gui_app.messagebox,
        "showerror",
        lambda title, message, **_kwargs: errors.append((title, message)),
    )

    app.lock_and_switch()

    assert app.root.withdrawn is True
    assert app.root.deiconified is True
    assert app.root.destroyed is True
    assert errors and "store unreadable" in errors[0][1]
