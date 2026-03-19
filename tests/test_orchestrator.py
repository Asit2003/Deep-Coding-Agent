from types import SimpleNamespace

from agent.orchestrator import (
    CodingOrchestrator,
    build_project_root,
    derive_project_name,
    merge_task_results,
    partition_tasks,
    resolve_project_target,
)
from config import AgentConfig


def test_partition_tasks_splits_independent_and_dependent() -> None:
    tasks = [
        {"id": 1, "description": "Inspect code", "depends_on": []},
        {"id": 2, "description": "Implement change", "depends_on": [1]},
        {"id": 3, "description": "Update docs", "depends_on": []},
    ]
    independent, dependent = partition_tasks(tasks)

    assert independent == [1, 3]
    assert dependent == [2]


def test_merge_task_results_updates_status_and_summary() -> None:
    tasks = [
        {"id": 1, "description": "Task 1", "status": "pending", "depends_on": []},
        {"id": 2, "description": "Task 2", "status": "pending", "depends_on": [1]},
    ]
    results = [
        {
            "task_id": 1,
            "status": "completed",
            "summary": "Implemented task 1",
            "files_touched": ["a.py"],
        },
        {
            "task_id": 2,
            "status": "blocked",
            "summary": "Need user input",
            "files_touched": [],
        },
    ]

    merged, task_results, completed_ids, failed_ids = merge_task_results(tasks, results)

    assert merged[0]["status"] == "completed"
    assert merged[0]["result"] == "Implemented task 1"
    assert merged[0]["files_touched"] == ["a.py"]

    assert merged[1]["status"] == "blocked"
    assert merged[1]["result"] == "Need user input"

    assert task_results == {"1": "Implemented task 1", "2": "Need user input"}
    assert completed_ids == [1]
    assert failed_ids == [2]


def test_derive_project_name_from_explicit_request_hint() -> None:
    name = derive_project_name("Create project named Fast API Portal with auth")
    assert name == "fast-api-portal-with-auth"


def test_derive_project_name_from_generic_request() -> None:
    name = derive_project_name("Build a task manager backend with tests and docs")
    assert name == "task-manager-backend"


def test_derive_project_name_ignores_polite_casual_phrasing() -> None:
    name = derive_project_name("Can you please build the frontend")
    assert name == "frontend"


def test_derive_project_name_extracts_concept_for_api_request() -> None:
    name = derive_project_name("Build a FastAPI endpoint for resume analyzer")
    assert name == "resume-analyzer-api"


def test_derive_project_name_type_for_domain_uses_type_prefix() -> None:
    name = derive_project_name("build a frontend for resume analyzer")
    assert name == "frontend-resume-analyzer"


def test_build_project_root_uses_configured_base_path() -> None:
    root = build_project_root("workspace/apps", "My Portal")
    assert root == "workspace/apps/my-portal"


def test_resolve_project_target_prefers_explicit_working_directory() -> None:
    project_name, project_root = resolve_project_target(
        configured_projects_root="project",
        user_request="Build a customer support API",
        project_name="",
        working_directory="apps/support-api",
    )

    assert project_name == "support-api"
    assert project_root == "apps/support-api"


def test_run_verifies_plan_file_before_graph_invoke(monkeypatch) -> None:
    config = AgentConfig(
        api_key="stub-openai-key",
        plan_file="tmp_plan_orchestrator_verify.md",
    )
    orchestrator = CodingOrchestrator(config=config)

    verify_calls: list[tuple[str, str, int]] = []

    def _fake_verify(task: str, plan_file: str, max_steps: int) -> str:
        verify_calls.append((task, plan_file, max_steps))
        return "Verified plan file (no updates required)"

    captured_payload: list[dict] = []

    def _fake_invoke(payload: dict) -> dict:
        captured_payload.append(payload)
        return {"messages": [{"role": "assistant", "content": "Deep agent done"}]}

    monkeypatch.setattr("agent.orchestrator.plan_ops.verify_plan_file", _fake_verify)
    orchestrator.graph = SimpleNamespace(invoke=_fake_invoke)
    orchestrator.graph_project_root = "project/demo"
    monkeypatch.setattr(
        orchestrator.test_runner,
        "run",
        lambda cwd=None: {"passed": True, "exit_code": 0, "output": f"ok:{cwd}"},
    )

    result = orchestrator.run("Build endpoint", project_name="demo")

    assert "Deep agent done" in result["final_summary"]
    assert captured_payload
    assert "Build endpoint" in captured_payload[0]["messages"][0]["content"]
    assert result["project_root"] == "project/demo"
    assert result["working_directory"] == "project/demo"
    assert verify_calls == [
        ("Build endpoint", "tmp_plan_orchestrator_verify.md", config.planning_max_steps)
    ]


def test_run_returns_preflight_error_when_plan_verification_fails(monkeypatch) -> None:
    config = AgentConfig(
        api_key="",
        plan_file="tmp_plan_orchestrator_verify_error.md",
    )
    orchestrator = CodingOrchestrator(config=config)

    monkeypatch.setattr(
        "agent.orchestrator.plan_ops.verify_plan_file",
        lambda **_: "Error: preflight failed",
    )

    invoke_called = {"value": False}

    def _fake_invoke(_: dict) -> dict:
        invoke_called["value"] = True
        return {"final_summary": "should not happen"}

    orchestrator.graph = SimpleNamespace(invoke=_fake_invoke)
    result = orchestrator.run("Build endpoint")

    assert invoke_called["value"] is False
    assert result["final_summary"] == "Plan preflight failed: Error: preflight failed"


def test_build_deep_agent_registers_shell_tool(monkeypatch) -> None:
    config = AgentConfig(api_key="stub-openai-key")
    orchestrator = CodingOrchestrator(config=config)
    captured: dict[str, object] = {}

    monkeypatch.setattr("agent.orchestrator.ChatOpenAI", lambda **kwargs: kwargs)
    monkeypatch.setattr("agent.orchestrator.FilesystemBackend", lambda **kwargs: kwargs)

    def _fake_create_deep_agent(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"graph": "ok"}

    monkeypatch.setattr("agent.orchestrator.create_deep_agent", _fake_create_deep_agent)

    result = orchestrator._build_deep_agent(project_root="project/demo")

    tool_names = [tool.name for tool in captured["tools"]]  # type: ignore[index]
    assert result == {"graph": "ok"}
    assert "run_shell" in tool_names
