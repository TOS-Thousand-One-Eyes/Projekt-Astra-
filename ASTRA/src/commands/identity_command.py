from commands.base import Command


class IdentityCommand(Command):
    help_text = (
        "- who am i / identity status - show the active local profile\n"
        "- identity profiles - show configured profile names\n"
        "- identity storage - show the active persistent data location"
    )

    def __init__(self, identity=None, identity_manager=None, logger=None):
        super().__init__(logger)
        self.identity = identity
        self.identity_manager = identity_manager

    def handle(self, message, normalized):
        if normalized in {
            "who am i",
            "whoami",
            "identity",
            "identity status",
            "profile",
            "profile status",
        }:
            return self._status()
        if normalized in {"identity profiles", "profiles", "user profiles"}:
            return self._profiles()
        if normalized in {"identity storage", "profile storage"}:
            return self._storage()
        if normalized.startswith("user switch ") or normalized.startswith(
            "identity switch "
        ):
            return (
                "Use the GUI `Lock / switch` button, or exit and restart the CLI. "
                "The PIN must be entered in a protected login prompt, never in chat."
            )
        return None

    def _status(self):
        if not self.identity:
            return "Identity profiles are not active in this legacy runtime."
        return (
            "Active identity:\n"
            f"- profile: {self.identity.display_name}\n"
            f"- user id: {self.identity.user_id}\n"
            f"- personal runtime data: {self.identity.data_dir}\n"
            f"- last seen version: {self._last_seen()}\n"
            "- PIN: never accepted through chat"
        )

    def _storage(self):
        if not self.identity:
            return "Identity profiles are not active in this legacy runtime."
        root = (
            self.identity_manager.data_dir
            if self.identity_manager
            else self.identity.data_dir.parent.parent
        )
        return (
            "Identity storage:\n"
            f"- root: {root}\n"
            f"- active profile: {self.identity.data_dir}\n"
            "- source updates do not replace this directory"
        )

    def _last_seen(self):
        if not self.identity_manager:
            return "unavailable"
        return self.identity_manager.last_seen_version(self.identity.user_id) or "not recorded"

    def _profiles(self):
        if not self.identity_manager:
            if self.identity:
                return f"Available profile in this runtime: {self.identity.display_name}"
            return "Identity profile manager is not configured."
        profiles = self.identity_manager.list_profiles()
        lines = ["Local identity profiles:"]
        for item in profiles:
            configured = "PIN ready" if item["pin_configured"] else "PIN setup required"
            active = (
                " (active)"
                if self.identity and item["id"] == self.identity.user_id
                else ""
            )
            lines.append(
                f"- {item['display_name']} [{item['id']}]: {configured}; "
                f"last seen {item.get('last_seen_version') or 'not recorded'}{active}"
            )
        return "\n".join(lines)
