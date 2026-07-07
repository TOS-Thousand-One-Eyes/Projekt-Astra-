from datetime import datetime

import pytest

from automation.reminder_manager import ReminderManager, ReminderParseError, parse_due_at
from commands.reminder_command import ReminderCommand
from commands.registry import build_default_registry
from memory.memory_manager import MemoryManager


def fixed_now():
    return datetime(2026, 7, 6, 8, 30)


def test_parse_due_at_supports_absolute_date_and_relative_words():
    assert parse_due_at("2026-07-07 09:15", now=fixed_now()) == datetime(2026, 7, 7, 9, 15)
    assert parse_due_at("2026-07-07", now=fixed_now()) == datetime(2026, 7, 7, 9, 0)
    assert parse_due_at("today 10:00", now=fixed_now()) == datetime(2026, 7, 6, 10, 0)
    assert parse_due_at("tomorrow 10:00", now=fixed_now()) == datetime(2026, 7, 7, 10, 0)


def test_parse_due_at_rejects_unclear_time():
    with pytest.raises(ReminderParseError, match="YYYY-MM-DD"):
        parse_due_at("next week", now=fixed_now())


def test_reminder_manager_creates_persists_lists_and_completes_one_off(tmp_path):
    manager = ReminderManager(data_dir=tmp_path, now_provider=fixed_now)

    reminder = manager.create("Review ASTRA tests", "2026-07-06 08:00")

    assert reminder["id"] == "REM-0001"
    assert manager.due() == [reminder]

    reloaded = ReminderManager(data_dir=tmp_path, now_provider=fixed_now)
    completed = reloaded.complete("REM-0001")

    assert completed["status"] == "done"
    assert reloaded.list(status="open") == []
    assert reloaded.list(status="done")[0]["title"] == "Review ASTRA tests"


def test_reminder_manager_daily_completion_rolls_forward(tmp_path):
    manager = ReminderManager(data_dir=tmp_path, now_provider=fixed_now)
    manager.create("Daily briefing", "today 08:00", recurrence="daily")

    completed = manager.complete("Daily briefing")

    assert completed["status"] == "open"
    assert completed["due_at"] == "2026-07-07 08:00"
    assert completed["events"][-1]["event"] == "completed-instance"


def test_reminder_command_creates_lists_due_and_completes(tmp_path):
    manager = ReminderManager(data_dir=tmp_path, now_provider=fixed_now)
    command = ReminderCommand(reminders=manager)

    created = command.handle(
        "remind me to Review ASTRA tests at 2026-07-06 08:00",
        "remind me to review astra tests at 2026-07-06 08:00",
    )
    due = command.handle("reminders due", "reminders due")
    completed = command.handle("reminder done REM-0001", "reminder done rem-0001")

    assert "REM-0001" in created
    assert "Review ASTRA tests" in due
    assert "Reminder completed" in completed


def test_reminder_command_creates_daily_reminder(tmp_path):
    manager = ReminderManager(data_dir=tmp_path, now_provider=fixed_now)
    command = ReminderCommand(reminders=manager)

    response = command.handle(
        "remind me to Daily briefing every day at 09:00",
        "remind me to daily briefing every day at 09:00",
    )

    reminder = manager.list()[0]
    assert "daily" in response
    assert reminder["recurrence"] == "daily"
    assert reminder["due_at"] == "2026-07-06 09:00"


def test_default_registry_shares_reminders_with_jarvis_status(tmp_path, config):
    memory = MemoryManager(data_dir=tmp_path / "memory")
    reminders = ReminderManager(data_dir=tmp_path / "runtime", now_provider=fixed_now)
    registry = build_default_registry(config, memory, reminders=reminders)

    registry.dispatch("remind me to Review ASTRA tests at 2026-07-06 08:00")
    response = registry.dispatch("jarvis status").response

    assert "open reminders: 1" in response
    assert "due reminders: 1" in response
    assert "REM-0001 - Review ASTRA tests" in response
