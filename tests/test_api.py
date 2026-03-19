from datetime import UTC, datetime

from fastapi.testclient import TestClient

from agent_api.app import create_app
from agent_api.schemas import AgentRunCreateRequest
from agent_api.service import AgentRunManager, AgentRunRecord, RunNotFoundError


class _DummyExecutor:
    def __init__(self) -> None:
        self.submissions: list[tuple[object, tuple[object, ...]]] = []

    def submit(self, fn: object, *args: object) -> None:
        self.submissions.append((fn, args))
        return None

    def shutdown(self, wait: bool = False, cancel_futures: bool = False) -> None:
        return None


class FakeRunManager:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.record = AgentRunRecord(
            run_id="run-123",
            status="completed",
            prompt="Build a production FastAPI service",
            project_name="agent-api",
            working_directory="project/agent-api",
            plan_file="project/agent-api/.deep-agent/runs/run-123/agent_plan.md",
            created_at=now,
            started_at=now,
            completed_at=now,
            final_summary="Finished successfully.",
            agent_success=True,
            result={"final_summary": "Finished successfully."},
        )

    @property
    def total_runs(self) -> int:
        return 1

    @property
    def active_runs(self) -> int:
        return 0

    def submit(self, payload: AgentRunCreateRequest) -> AgentRunRecord:
        self.record.prompt = payload.prompt
        if payload.working_directory:
            self.record.working_directory = payload.working_directory
        if payload.project_name:
            self.record.project_name = payload.project_name
        return self.record

    def get(self, run_id: str) -> AgentRunRecord:
        if run_id != self.record.run_id:
            raise RunNotFoundError(f"Run '{run_id}' was not found")
        return self.record

    def list_runs(self, limit: int = 20) -> list[AgentRunRecord]:
        return [self.record][:limit]


def test_run_manager_submit_derives_working_directory() -> None:
    manager = AgentRunManager(max_workers=1)
    real_executor = manager._executor
    manager._executor = _DummyExecutor()
    real_executor.shutdown(wait=False, cancel_futures=True)

    record = manager.submit(
        AgentRunCreateRequest(prompt="Build a task tracking API with tests")
    )

    assert record.status == "queued"
    assert record.project_name == "task-tracking-api"
    assert record.working_directory == "project/task-tracking-api"
    assert record.plan_file.startswith(record.working_directory)


def test_run_manager_submit_rejects_paths_outside_workspace() -> None:
    manager = AgentRunManager(max_workers=1)
    real_executor = manager._executor
    manager._executor = _DummyExecutor()
    real_executor.shutdown(wait=False, cancel_futures=True)

    try:
        manager.submit(
            AgentRunCreateRequest(
                prompt="Build an API",
                working_directory="../outside-workspace",
            )
        )
    except ValueError as err:
        assert "outside workspace root" in str(err)
    else:
        raise AssertionError("Expected ValueError for path traversal")


def test_create_run_endpoint_returns_accepted_response() -> None:
    with TestClient(create_app(run_manager=FakeRunManager())) as client:
        response = client.post(
            "/api/v1/agent/runs",
            json={
                "prompt": "Build the API layer",
                "working_directory": "project/custom-api",
                "project_name": "custom-api",
            },
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["prompt"] == "Build the API layer"
    assert payload["project_name"] == "custom-api"
    assert payload["working_directory"] == "project/custom-api"
    assert payload["status"] == "completed"
    assert payload["status_url"].endswith("/api/v1/agent/runs/run-123")


def test_get_run_endpoint_returns_result_payload() -> None:
    with TestClient(create_app(run_manager=FakeRunManager())) as client:
        response = client.get("/api/v1/agent/runs/run-123")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "run-123"
    assert payload["result"] == {"final_summary": "Finished successfully."}


def test_health_endpoint_reports_counts() -> None:
    with TestClient(create_app(run_manager=FakeRunManager())) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["total_runs"] == 1
    assert payload["active_runs"] == 0
