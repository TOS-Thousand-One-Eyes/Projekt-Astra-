import ast
from pathlib import Path


class CodeInspectionError(Exception):
    pass


class CodeInspector:
    """Read-only Python source inspection for programming assistance."""

    def inspect(self, path):
        source_path = Path(str(path).strip().strip('"'))
        if not source_path.exists():
            raise FileNotFoundError(f"Code file not found: {path}")
        if not source_path.is_file():
            raise CodeInspectionError(f"Not a file: {path}")
        if source_path.suffix != ".py":
            raise CodeInspectionError("Only Python files are supported right now.")
        text = source_path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text)
        except SyntaxError as error:
            raise CodeInspectionError(f"Python syntax error at line {error.lineno}: {error.msg}") from error
        return {
            "path": str(source_path),
            "lines": len(text.splitlines()),
            "classes": class_names(tree),
            "functions": function_names(tree),
            "imports": import_names(tree),
            "todos": todo_lines(text),
        }


def class_names(tree):
    return [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def function_names(tree):
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def import_names(tree):
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names.append(module if node.level == 0 else "." * node.level + module)
    return sorted(set(names))


def todo_lines(text):
    results = []
    for index, line in enumerate(text.splitlines(), start=1):
        if "TODO" in line or "FIXME" in line:
            results.append({"line": index, "text": line.strip()})
    return results
