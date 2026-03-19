import shutil
from pathlib import Path
import sys

import pytest

from agent.coding_agent import DeepCodingAgent, _scope_project_path
from config import AgentConfig


def test_scope_project_path_prefixes_relative_path() -> None:
    scoped = _scope_project_path("src/main.py", "project/my-app")
    assert scoped == "project/my-app/src/main.py"


def test_scope_project_path_keeps_existing_scoped_path() -> None:
    scoped = _scope_project_path("project/my-app/app.py", "project/my-app")
    assert scoped == "project/my-app/app.py"


def test_scope_project_path_rejects_traversal() -> None:
    with pytest.raises(ValueError):
        _scope_project_path("../outside.py", "project/my-app")


def test_build_tool_bindings_includes_run_shell() -> None:
    agent = DeepCodingAgent(AgentConfig(api_key="stub-key"))
    project_root = Path("tests/tmp_shell_project")
    try:
        project_root.mkdir(parents=True, exist_ok=True)

        bindings = agent._build_tool_bindings("tests/tmp_shell_project")

        assert "run_shell" in bindings
        result = bindings["run_shell"].fn(
            command=[sys.executable, "-c", "print('ok')"],
        )
        assert result["ok"] is True
        assert result["cwd"] == "tests/tmp_shell_project"
    finally:
        shutil.rmtree(project_root, ignore_errors=True)
