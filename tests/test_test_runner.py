from pathlib import Path

import agent.test_builder as test_builder
from agent.test_builder import TestRunner as AgentTestRunner
from config import AgentConfig


class _CompletedProcess:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_test_runner_executes_in_requested_workspace_directory(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(
        command: str,
        *,
        cwd: Path,
        shell: bool,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> _CompletedProcess:
        captured["command"] = command
        captured["cwd"] = cwd
        captured["shell"] = shell
        captured["check"] = check
        captured["capture_output"] = capture_output
        captured["text"] = text
        return _CompletedProcess(returncode=0, stdout="ok")

    monkeypatch.setattr(test_builder.subprocess, "run", fake_run)
    runner = AgentTestRunner(AgentConfig(run_tests_command="pytest -q"))

    result = runner.run(cwd="tests")

    assert result["passed"] is True
    assert captured["command"] == "pytest -q"
    assert captured["cwd"] == test_builder.WORKSPACE_ROOT / "tests"
