import pytest

from commands.code_command import CodeCommand
from commands.registry import build_default_registry
from dev.code_inspector import CodeInspectionError, CodeInspector
from memory.memory_manager import MemoryManager


def test_code_inspector_reads_python_structure(tmp_path):
    path = tmp_path / "sample.py"
    path.write_text(
        "\n".join(
            [
                "import os",
                "from pathlib import Path",
                "",
                "class Worker:",
                "    def run(self):",
                "        pass",
                "",
                "async def load():",
                "    pass",
                "",
                "# TODO: add tests",
            ]
        ),
        encoding="utf-8",
    )

    info = CodeInspector().inspect(path)

    assert info["lines"] == 11
    assert info["classes"] == ["Worker"]
    assert info["functions"] == ["load", "run"]
    assert info["imports"] == ["os", "pathlib"]
    assert info["todos"][0]["line"] == 11


def test_code_inspector_rejects_non_python_files(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("hello", encoding="utf-8")

    with pytest.raises(CodeInspectionError, match="Python"):
        CodeInspector().inspect(path)


def test_code_inspector_reports_syntax_errors(tmp_path):
    path = tmp_path / "broken.py"
    path.write_text("def broken(:\n    pass\n", encoding="utf-8")

    with pytest.raises(CodeInspectionError, match="syntax"):
        CodeInspector().inspect(path)


def test_code_command_formats_inspection(tmp_path):
    path = tmp_path / "sample.py"
    path.write_text("class Tool:\n    pass\n", encoding="utf-8")
    command = CodeCommand()

    response = command.handle(f"code inspect {path}", f"code inspect {path}".lower())

    assert "Code inspection:" in response
    assert "classes: Tool" in response


def test_default_registry_dispatches_code_inspector_with_injected_adapter(tmp_path, config):
    class StubCodeInspector:
        def inspect(self, path):
            return {
                "path": path,
                "lines": 1,
                "classes": ["A"],
                "functions": ["b"],
                "imports": ["c"],
                "todos": [],
            }

    memory = MemoryManager(data_dir=tmp_path / "memory")
    registry = build_default_registry(config, memory, code=StubCodeInspector())

    response = registry.dispatch("code inspect demo.py").response

    assert "classes: A" in response
    assert "functions: b" in response
