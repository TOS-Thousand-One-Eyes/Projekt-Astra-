from commands.base import Command
from dev.code_inspector import CodeInspectionError, CodeInspector


class CodeCommand(Command):
    help_text = "- code inspect <path> - inspect a Python file's structure"

    def __init__(self, inspector=None, logger=None):
        super().__init__(logger)
        self.inspector = inspector or CodeInspector()

    def handle(self, message, normalized):
        if normalized.startswith("code inspect "):
            return self._inspect(message.strip()[len("code inspect "):])
        return None

    def _inspect(self, path):
        try:
            info = self.inspector.inspect(path)
        except FileNotFoundError as error:
            return str(error)
        except CodeInspectionError as error:
            return str(error)
        return format_code_info(info)


def format_code_info(info):
    classes = ", ".join(info["classes"]) if info["classes"] else "none"
    functions = ", ".join(info["functions"]) if info["functions"] else "none"
    imports = ", ".join(info["imports"]) if info["imports"] else "none"
    todo_count = len(info["todos"])
    return (
        f"Code inspection: {info['path']}\n"
        f"- lines: {info['lines']}\n"
        f"- classes: {classes}\n"
        f"- functions: {functions}\n"
        f"- imports: {imports}\n"
        f"- TODO/FIXME: {todo_count}"
    )
