import pytest

from actions.system_action_manager import SystemActionError, SystemActionManager
from commands.registry import build_default_registry
from commands.system_action_command import SystemActionCommand
from memory.memory_manager import MemoryManager


class StubExecutor:
    def __init__(self):
        self.executed = []

    def execute(self, action):
        self.executed.append(action["id"])
        return f"stub:{action['target']}"


def test_system_action_manager_requires_approval_before_execution(tmp_path):
    manager = SystemActionManager(data_dir=tmp_path, executor=StubExecutor())
    action = manager.propose("open_path", "C:/Temp/demo.txt")

    assert action["id"] == "SYS-0001"
    assert action["status"] == "pending"
    with pytest.raises(SystemActionError, match="approved"):
        manager.execute("SYS-0001")


def test_system_action_manager_approves_and_executes_with_injected_executor(tmp_path):
    executor = StubExecutor()
    manager = SystemActionManager(data_dir=tmp_path, executor=executor)
    manager.propose("open_path", "C:/Temp/demo.txt")

    approved = manager.approve("SYS-0001")
    assert approved["status"] == "approved"

    executed = manager.execute("SYS-0001")

    assert executed["status"] == "executed"
    assert executed["result"] == "stub:C:/Temp/demo.txt"
    assert executor.executed == ["SYS-0001"]


def test_system_action_manager_persists_queue(tmp_path):
    manager = SystemActionManager(data_dir=tmp_path, executor=StubExecutor())
    manager.propose("open_path", "C:/Temp/demo.txt")

    reloaded = SystemActionManager(data_dir=tmp_path, executor=StubExecutor())

    assert reloaded.list()[0]["target"] == "C:/Temp/demo.txt"


def test_system_action_command_full_flow(tmp_path):
    manager = SystemActionManager(data_dir=tmp_path, executor=StubExecutor())
    command = SystemActionCommand(system_actions=manager)

    queued = command.handle("system propose open C:/Temp/demo.txt", "system propose open c:/temp/demo.txt")
    listed = command.handle("system actions", "system actions")
    approved = command.handle("system approve SYS-0001", "system approve sys-0001")
    executed = command.handle("system run SYS-0001", "system run sys-0001")

    assert "System action queued" in queued
    assert "SYS-0001 [pending]" in listed
    assert "System action approved" in approved
    assert "System action executed" in executed


def test_system_action_command_rejects_pending_action(tmp_path):
    manager = SystemActionManager(data_dir=tmp_path, executor=StubExecutor())
    command = SystemActionCommand(system_actions=manager)
    command.handle("system propose open C:/Temp/demo.txt", "system propose open c:/temp/demo.txt")

    response = command.handle("system reject SYS-0001", "system reject sys-0001")

    assert "System action rejected" in response
    assert manager.list(status="rejected")[0]["id"] == "SYS-0001"


def test_default_registry_shares_system_actions_with_jarvis_status(tmp_path, config):
    memory = MemoryManager(data_dir=tmp_path / "memory")
    system_actions = SystemActionManager(data_dir=tmp_path / "runtime", executor=StubExecutor())
    registry = build_default_registry(config, memory, system_actions=system_actions)

    registry.dispatch("system propose open C:/Temp/demo.txt")
    response = registry.dispatch("jarvis status").response

    assert "pending system actions: 1" in response
    assert "approved system actions: 0" in response
