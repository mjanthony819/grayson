"""Windows console windows must never flash for subprocess work.

Grayson is a windowed app (pythonw / PyInstaller --windowed). Any
subprocess spawned without CREATE_NO_WINDOW pops a visible console on
Windows. This AST check runs everywhere and guards every call site.
"""
import ast
import pathlib


def test_subprocess_calls_hide_console_window():
    pkg = pathlib.Path(__file__).resolve().parents[1] / "grayson"
    offenders = []
    for py in pkg.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "subprocess"
                and node.func.attr in {"run", "Popen", "call", "check_call", "check_output"}
            ):
                has_flag = any(
                    k.arg == "creationflags" or k.arg is None  # **_NO_WINDOW splat
                    for k in node.keywords
                )
                if not has_flag:
                    offenders.append(f"{py.name}:{node.lineno} subprocess.{node.func.attr}")
    assert not offenders, "spawned without CREATE_NO_WINDOW: " + ", ".join(offenders)
