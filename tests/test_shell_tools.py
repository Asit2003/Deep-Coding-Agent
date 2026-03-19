import sys

from tools.shell_tools import make_run_shell_tool
from utils import shell as shell_ops


def test_run_shell_command_allows_python_script() -> None:
    result = shell_ops.run_shell_command(
        args=[sys.executable, "-c", "print('ok')"],
        base_directory=".",
    )

    assert result["ok"] is True
    assert result["exit_code"] == 0
    assert result["stdout"] == "ok"
    assert result["timed_out"] is False


def test_run_shell_command_rejects_non_allowlisted_command() -> None:
    result = shell_ops.run_shell_command(
        args=["powershell", "-Command", "Get-ChildItem"],
        base_directory=".",
    )

    assert result["ok"] is False
    assert "not allowlisted" in result["stderr"]


def test_run_shell_command_rejects_destructive_git_subcommand() -> None:
    result = shell_ops.run_shell_command(
        args=["git", "reset", "--hard"],
        base_directory=".",
    )

    assert result["ok"] is False
    assert "not allowed" in result["stderr"]


def test_run_shell_command_rejects_cwd_escape() -> None:
    result = shell_ops.run_shell_command(
        args=[sys.executable, "-c", "print('nope')"],
        cwd="../agent",
        base_directory="tests",
    )

    assert result["ok"] is False
    assert "must stay inside" in result["stderr"]


def test_run_shell_command_times_out() -> None:
    result = shell_ops.run_shell_command(
        args=[sys.executable, "-c", "import time; time.sleep(2)"],
        base_directory=".",
        timeout_seconds=1,
    )

    assert result["ok"] is False
    assert result["timed_out"] is True


def test_run_shell_command_truncates_large_output() -> None:
    result = shell_ops.run_shell_command(
        args=[sys.executable, "-c", "print('x' * 400)"],
        base_directory=".",
        max_output_chars=220,
    )

    assert result["ok"] is True
    assert "[truncated" in result["stdout"]


def test_make_run_shell_tool_uses_scoped_base_directory() -> None:
    tool = make_run_shell_tool(base_directory="tests")
    result = tool.invoke(
        {
            "command": [sys.executable, "-c", "import os; print(os.getcwd())"],
        }
    )

    assert result["ok"] is True
    assert result["cwd"] == "tests"
