from commands.base import Command


class DiagnosticsCommand(Command):

    TRIGGERS = ("diagnostics", "status")

    help_text = "- diagnostics / status - check whether anything went wrong this session"

    def __init__(self, config, memory, logger=None):
        super().__init__(logger)
        self.config = config
        self.memory = memory

    def handle(self, message, normalized):
        if normalized not in self.TRIGGERS:
            return None

        problems = []
        for warning in self.config.load_warnings:
            problems.append(f"- config: {warning}")
        for warning in self.memory.load_warnings():
            problems.append(f"- memory: {warning}")
        if self.logger and self.config.log_to_file and not self.logger.log_to_file:
            problems.append(
                "- logging: writing to the log file failed earlier; "
                "file logging is off for the rest of this session."
            )

        if not problems:
            return "Everything looks good - no warnings this session."
        return "Here's what needs attention:\n" + "\n".join(problems)
