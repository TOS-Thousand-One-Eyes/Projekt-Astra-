import pytest

from actions.action_manager import ActionManager
from commands.action_command import ActionCommand
from commands.registry import build_default_registry
from learning.learning_manager import LearningManager
from memory.memory_manager import MemoryManager


def test_action_manager_creates_persists_and_completes_task(tmp_path):
    actions = ActionManager(data_dir=tmp_path)

    task = actions.create_task("Write action tests", priority="urgent", due="2026-07-10")

    assert task["id"] == "TASK-0001"
    assert task["priority"] == "high"
    assert task["due"] == "2026-07-10"

    reloaded = ActionManager(data_dir=tmp_path)
    assert reloaded.list_tasks()[0]["title"] == "Write action tests"

    completed = reloaded.complete_task("TASK-0001")

    assert completed["status"] == "done"
    assert completed["completed_at"] is not None
    assert reloaded.list_tasks(status="open") == []


def test_action_manager_rejects_bad_due_date(tmp_path):
    actions = ActionManager(data_dir=tmp_path)

    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        actions.create_task("Bad date", due="tomorrow")


def test_action_manager_plan_goal_creates_tasks_and_decision(tmp_path):
    actions = ActionManager(data_dir=tmp_path)

    plan = actions.plan_goal("Ship JARVIS action layer")

    assert plan["id"] == "PLAN-0001"
    assert len(plan["tasks"]) == 4
    assert all(task["plan_id"] == "PLAN-0001" for task in plan["tasks"])
    assert actions.list_decisions()[0]["title"] == "Created action plan PLAN-0001"


def test_action_command_creates_lists_and_completes_task(tmp_path):
    actions = ActionManager(data_dir=tmp_path)
    command = ActionCommand(actions=actions)

    created = command.handle(
        "task Add a local action layer priority high due 2026-07-10",
        "task add a local action layer priority high due 2026-07-10",
    )
    listed = command.handle("tasks", "tasks")
    completed = command.handle("done TASK-0001", "done task-0001")
    done_list = command.handle("tasks done", "tasks done")

    assert "TASK-0001" in created
    assert "Add a local action layer" in listed
    assert "Task completed" in completed
    assert "[done]" in done_list


def test_action_command_records_decisions(tmp_path):
    actions = ActionManager(data_dir=tmp_path)
    command = ActionCommand(actions=actions)

    response = command.handle(
        "decide Keep ASTRA local-first: avoids cloud dependency",
        "decide keep astra local-first: avoids cloud dependency",
    )
    listed = command.handle("decisions", "decisions")

    assert "DEC-0001" in response
    assert "Keep ASTRA local-first" in listed
    assert "avoids cloud dependency" in listed


def test_default_registry_shares_actions_with_jarvis_status(tmp_path, config):
    memory = MemoryManager(data_dir=tmp_path / "memory")
    learning = LearningManager(data_dir=tmp_path / "runtime")
    actions = ActionManager(data_dir=tmp_path / "runtime")
    registry = build_default_registry(config, memory, learning=learning, actions=actions)

    registry.dispatch("task Verify shared action state")
    response = registry.dispatch("jarvis status").response

    assert "open tasks: 1" in response
    assert "TASK-0001 - Verify shared action state" in response
