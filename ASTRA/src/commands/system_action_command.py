from actions.system_action_manager import SystemActionError, SystemActionManager
from commands.base import Command


class SystemActionCommand(Command):
    help_text = (
        "- system propose open <path> - queue a desktop open action for approval\n"
        "- system actions / system actions all - list queued system actions\n"
        "- system approve <id> - approve a pending system action\n"
        "- system reject <id> - reject a pending system action\n"
        "- system run <id> - execute an approved system action"
    )

    def __init__(self, system_actions=None, logger=None):
        super().__init__(logger)
        self.system_actions = system_actions or SystemActionManager()

    def handle(self, message, normalized):
        if normalized.startswith("system propose open "):
            return self._propose_open(message.strip()[len("system propose open "):])
        if normalized in ("system actions", "system actions pending"):
            return self._list("pending")
        if normalized in ("system actions all", "all system actions"):
            return self._list("all")
        if normalized.startswith("system approve "):
            return self._approve(message.strip()[len("system approve "):])
        if normalized.startswith("system reject "):
            return self._reject(message.strip()[len("system reject "):])
        if normalized.startswith("system run "):
            return self._run(message.strip()[len("system run "):])
        return None

    def _propose_open(self, target):
        try:
            action = self.system_actions.propose("open_path", target, reason="Open explicit local path")
        except ValueError as error:
            return f"I couldn't queue that system action: {error}"
        return (
            f"System action queued: {action['id']} - open {action['target']}.\n"
            f"Approve it with `system approve {action['id']}` before running."
        )

    def _list(self, status):
        actions = self.system_actions.list(status=status)
        if not actions:
            return "No system actions."
        return "System actions:\n" + "\n".join(format_system_action(action) for action in actions)

    def _approve(self, identifier):
        try:
            action = self.system_actions.approve(identifier)
        except FileNotFoundError:
            return f"I couldn't find a system action matching: {identifier}"
        except (ValueError, SystemActionError) as error:
            return str(error)
        return f"System action approved: {action['id']} - {action['kind']} {action['target']}."

    def _reject(self, identifier):
        try:
            action = self.system_actions.reject(identifier)
        except FileNotFoundError:
            return f"I couldn't find a system action matching: {identifier}"
        except (ValueError, SystemActionError) as error:
            return str(error)
        return f"System action rejected: {action['id']}."

    def _run(self, identifier):
        try:
            action = self.system_actions.execute(identifier)
        except FileNotFoundError:
            return f"I couldn't find a system action matching: {identifier}"
        except (ValueError, SystemActionError) as error:
            return str(error)
        except Exception as error:
            if self.logger:
                self.logger.error(f"System action execution failed: {type(error).__name__}: {error}")
            return f"System action failed: {error}"
        return f"System action executed: {action['id']} - {action['result']}."


def format_system_action(action):
    return (
        f"- {action['id']} [{action.get('status')}] "
        f"{action.get('kind')} {action.get('target')}"
    )
