"""Test-runner helper for orchestrator test execution stage."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import AgentConfig

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


def _resolve_test_directory(path_value: str | None) -> Path:
    """Resolve a test working directory inside the repository workspace."""
    if not path_value or not str(path_value).strip():
        return WORKSPACE_ROOT

    raw_path = Path(str(path_value).strip()).expanduser()
    resolved = (
        raw_path.resolve()
        if raw_path.is_absolute()
        else (WORKSPACE_ROOT / raw_path).resolve()
    )
    try:
        resolved.relative_to(WORKSPACE_ROOT)
    except ValueError as err:
        raise ValueError(
            f"Test working directory '{path_value}' is outside workspace root "
            f"'{WORKSPACE_ROOT.as_posix()}'"
        ) from err
    return resolved


@dataclass
class TestRunner:
    """Runs repository test command and captures diagnostics."""

    config: AgentConfig

    def run(self, cwd: str | None = None) -> dict[str, Any]:
        """Execute configured test command and return structured output."""
        command = self.config.run_tests_command.strip()
        if not command:
            return {
                "passed": True,
                "exit_code": 0,
                "output": "No test command configured.",
            }

        try:
            test_directory = _resolve_test_directory(cwd)
        except ValueError as err:
            return {
                "passed": False,
                "exit_code": -1,
                "output": str(err),
            }

        try:
            completed = subprocess.run(
                command,
                cwd=test_directory,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as err:
            return {
                "passed": False,
                "exit_code": -1,
                "output": f"Unable to execute tests: {err}",
            }

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if stdout and stderr:
            output = f"{stdout}\n\n{stderr}"
        else:
            output = stdout or stderr or "(no test output)"

        return {
            "passed": completed.returncode == 0,
            "exit_code": completed.returncode,
            "output": output,
        }
