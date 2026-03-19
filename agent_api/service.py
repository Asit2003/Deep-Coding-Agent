"""Background run manager for the FastAPI service."""

from __future__ import annotations

import logging
import os
import posixpath
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from threading import Lock
from typing import Any
from uuid import uuid4

from agent.orchestrator import CodingOrchestrator, resolve_project_target
from agent_api.schemas import AgentRunCreateRequest, AgentRunResponse, RunStatus
from config import settings

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def _resolve_api_worker_count(explicit: int | None = None) -> int:
    """Determine how many run workers the API should maintain."""
    if explicit is not None:
        return max(1, explicit)

    raw_value = os.getenv("AGENT_API_MAX_WORKERS", "4").strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        return 4
    return max(1, parsed)


def _build_run_plan_file(working_directory: str, run_id: str) -> str:
    """Build a unique per-run plan-file path inside the target directory."""
    run_root = posixpath.join(".deep-agent", "runs", run_id)
    if working_directory == ".":
        return posixpath.join(run_root, "agent_plan.md")
    return posixpath.join(working_directory, run_root, "agent_plan.md")


def _agent_succeeded(result: dict[str, Any]) -> bool:
    """Compute whether the agent achieved a fully successful outcome."""
    if "tests_passed" in result:
        final_summary = str(result.get("final_summary", "")).strip().lower()
        blocked_prefixes = (
            "plan preflight failed:",
            "execution blocked:",
            "failed to initialize deep agent:",
            "deep agent execution failed:",
        )
        if any(final_summary.startswith(prefix) for prefix in blocked_prefixes):
            return False
        return bool(result.get("tests_passed", False))

    tasks = result.get("plan_tasks", [])
    all_completed = bool(tasks) and all(
        str(task.get("status", "")).strip() == "completed" for task in tasks
    )
    return (
        bool(result.get("verifier_approved", False))
        and bool(result.get("tests_passed", False))
        and all_completed
    )


class RunNotFoundError(KeyError):
    """Raised when an API consumer asks for an unknown run."""


@dataclass
class AgentRunRecord:
    """In-memory state for one submitted run."""

    run_id: str
    status: RunStatus
    prompt: str
    project_name: str
    working_directory: str
    plan_file: str
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    final_summary: str | None = None
    agent_success: bool | None = None
    error: str | None = None
    result: dict[str, Any] | None = None

    def to_response(self, *, include_result: bool) -> AgentRunResponse:
        """Convert an in-memory run record into an API response model."""
        return AgentRunResponse(
            run_id=self.run_id,
            status=self.status,
            prompt=self.prompt,
            project_name=self.project_name,
            working_directory=self.working_directory,
            plan_file=self.plan_file,
            agent_success=self.agent_success,
            final_summary=self.final_summary,
            error=self.error,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            result=deepcopy(self.result) if include_result else None,
        )


class AgentRunManager:
    """Queue and track agent executions in background threads."""

    def __init__(self, max_workers: int | None = None) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=_resolve_api_worker_count(max_workers),
            thread_name_prefix="deep-agent-api",
        )
        self._lock = Lock()
        self._runs: dict[str, AgentRunRecord] = {}
        self._workspace_locks: dict[str, Lock] = {}

    @property
    def total_runs(self) -> int:
        """Return the number of tracked runs."""
        with self._lock:
            return len(self._runs)

    @property
    def active_runs(self) -> int:
        """Return the number of queued/running executions."""
        with self._lock:
            return sum(
                1 for run in self._runs.values() if run.status in {"queued", "running"}
            )

    def submit(self, payload: AgentRunCreateRequest) -> AgentRunRecord:
        """Create and queue a new agent run."""
        prompt = payload.prompt.strip()
        project_name, working_directory = resolve_project_target(
            configured_projects_root=str(settings.projects_root),
            user_request=prompt,
            project_name=payload.project_name or "",
            working_directory=payload.working_directory or "",
        )
        run_id = uuid4().hex
        record = AgentRunRecord(
            run_id=run_id,
            status="queued",
            prompt=prompt,
            project_name=project_name,
            working_directory=working_directory,
            plan_file=_build_run_plan_file(working_directory, run_id),
            created_at=utc_now(),
        )

        with self._lock:
            self._runs[run_id] = record

        logger.info("Queued agent run %s for %s", run_id, record.working_directory)
        self._executor.submit(self._run_agent, run_id)
        return self.get(run_id)

    def get(self, run_id: str) -> AgentRunRecord:
        """Fetch one run record by ID."""
        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                raise RunNotFoundError(f"Run '{run_id}' was not found")
            return deepcopy(record)

    def list_runs(self, limit: int = 20) -> list[AgentRunRecord]:
        """List the most recent run records."""
        with self._lock:
            ordered = sorted(
                self._runs.values(),
                key=lambda item: item.created_at,
                reverse=True,
            )
            return [deepcopy(item) for item in ordered[:limit]]

    def shutdown(self) -> None:
        """Shut down the worker pool."""
        self._executor.shutdown(wait=False, cancel_futures=False)

    def _get_workspace_lock(self, working_directory: str) -> Lock:
        """Return a stable lock for one workspace directory."""
        with self._lock:
            workspace_lock = self._workspace_locks.get(working_directory)
            if workspace_lock is None:
                workspace_lock = Lock()
                self._workspace_locks[working_directory] = workspace_lock
            return workspace_lock

    def _run_agent(self, run_id: str) -> None:
        """Execute one queued run and persist completion state."""
        with self._lock:
            record = self._runs[run_id]
            prompt = record.prompt
            project_name = record.project_name
            working_directory = record.working_directory
            plan_file = record.plan_file

        workspace_lock = self._get_workspace_lock(working_directory)
        logger.info(
            "Agent run %s waiting for workspace lock on %s",
            run_id,
            working_directory,
        )

        with workspace_lock:
            with self._lock:
                record = self._runs[run_id]
                record.status = "running"
                record.started_at = utc_now()

            logger.info("Starting agent run %s in %s", run_id, working_directory)

            try:
                config = replace(settings, plan_file=plan_file)
                orchestrator = CodingOrchestrator(config=config)
                result = orchestrator.run(
                    prompt,
                    project_name=project_name,
                    working_directory=working_directory,
                )
            except Exception as err:  # noqa: BLE001 - surface background failures.
                logger.exception("Agent run %s failed", run_id)
                with self._lock:
                    record = self._runs[run_id]
                    record.status = "failed"
                    record.error = str(err)
                    record.completed_at = utc_now()
                return

            final_summary = str(result.get("final_summary", "")).strip() or None
            normalized_directory = str(
                result.get("project_root")
                or result.get("working_directory")
                or working_directory
            ).strip()

            with self._lock:
                record = self._runs[run_id]
                record.status = "completed"
                record.working_directory = normalized_directory or working_directory
                record.completed_at = utc_now()
                record.result = deepcopy(result)
                record.final_summary = final_summary
                record.agent_success = _agent_succeeded(result)

            logger.info(
                "Completed agent run %s (agent_success=%s)",
                run_id,
                _agent_succeeded(result),
            )
