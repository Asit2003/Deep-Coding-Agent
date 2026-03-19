"""Test-runner helper for orchestrator test execution stage."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import AgentConfig

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class TestRunner:
    """Runs repository test command and captures diagnostics."""

    config: AgentConfig

    def run(self) -> dict[str, Any]:
        """Execute configured test command and return structured output."""
        command = self.config.run_tests_command.strip()
        if not command:
            return {
                "passed": True,
                "exit_code": 0,
                "output": "No test command configured.",
            }

        try:
            completed = subprocess.run(
                command,
                cwd=WORKSPACE_ROOT,
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
