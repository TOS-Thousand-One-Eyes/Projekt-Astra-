from commands.base import Command


class DiagnosticsCommand(Command):

    TRIGGERS = ("diagnostics", "status")
    help_text = "- diagnostics / status - check whether anything went wrong this session"

    def __init__(
        self,
        config,
        memory,
        logger=None,
        learning=None,
        self_learning=None,
        experience=None,
    ):
        super().__init__(logger)
        self.config = config
        self.memory = memory
        self.learning = learning
        self.self_learning = self_learning
        self.experience = experience

    def handle(self, message, normalized):
        if normalized not in self.TRIGGERS:
            return None

        problems = []
        for warning in self.config.load_warnings:
            problems.append(f"- config: {warning}")
        for warning in self.memory.load_warnings():
            problems.append(f"- memory: {warning}")
        for label, manager in (
            ("learning", self.learning),
            ("self-learning", self.self_learning),
            ("experience", self.experience),
        ):
            for warning in getattr(manager, "load_warnings", []) if manager else []:
                problems.append(f"- {label}: {warning}")
        health_check = getattr(self.self_learning, "health", None)
        if callable(health_check):
            try:
                health = health_check()
            except Exception as error:
                problems.append(
                    "- self-learning health: audit failed "
                    f"({type(error).__name__}: {error})"
                )
            else:
                if health.get("issues"):
                    problems.append(
                        "- self-learning health: "
                        f"{health.get('errors', 0)} error(s), "
                        f"{health.get('warnings', 0)} warning(s), "
                        f"{health.get('blocked_guidance', 0)} guidance blocked"
                    )
                    for item in health["issues"][:5]:
                        problems.append(
                            f"  - [{item.get('severity', 'unknown')}] "
                            f"{item.get('code', 'unknown')} "
                            f"({item.get('item_id', 'store')}): "
                            f"{item.get('message', 'No details')}"
                        )
        if self.logger and self.config.log_to_file and not self.logger.log_to_file:
            problems.append(
                "- logging: writing to the log file failed earlier; "
                "file logging is off for the rest of this session."
            )

        if not problems:
            return "Everything looks good - no warnings this session."
        return "Here's what needs attention:\n" + "\n".join(problems)
