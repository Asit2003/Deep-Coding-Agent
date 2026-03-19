"""Health-check routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from agent_api.dependencies import get_run_manager
from agent_api.schemas import HealthResponse
from agent_api.service import AgentRunManager, utc_now

router = APIRouter(tags=["health"])
RunManagerDependency = Annotated[AgentRunManager, Depends(get_run_manager)]


@router.get("/health", response_model=HealthResponse)
def healthcheck(run_manager: RunManagerDependency) -> HealthResponse:
    """Return service health and queue counters."""
    return HealthResponse(
        status="ok",
        service="deep-coding-agent-api",
        timestamp=utc_now(),
        total_runs=run_manager.total_runs,
        active_runs=run_manager.active_runs,
    )
