from commands.diagnostics_command import DiagnosticsCommand


class Config:
    load_warnings = []
    log_to_file = False


class Memory:
    def load_warnings(self):
        return []


class Manager:
    def __init__(self, warnings):
        self.load_warnings = warnings


def test_diagnostics_resurfaces_learning_and_experience_warnings():
    command = DiagnosticsCommand(
        Config(),
        Memory(),
        learning=Manager(["bad learning file"]),
        self_learning=Manager(["bad guidance file"]),
        experience=Manager(["bad experience file"]),
    )
    response = command.handle("status", "status")
    assert "learning: bad learning file" in response
    assert "self-learning: bad guidance file" in response
    assert "experience: bad experience file" in response


def test_diagnostics_old_constructor_still_works():
    response = DiagnosticsCommand(Config(), Memory()).handle("status", "status")
    assert "no warnings" in response
