"""Pydantic models used by the FastAPI service."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RunStatus = Literal["queued", "running", "completed", "failed"]


class AgentRunCreateRequest(BaseModel):
    """Run submission payload."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    prompt: str = Field(
        ...,
        min_length=1,
        description="Natural-language instruction for the coding agent.",
    )
    working_directory: str | None = Field(
        default=None,
        description=(
            "Optional workspace-relative directory where the agent should work."
        ),
    )
    project_name: str | None = Field(
        default=None,
        description="Optional project name hint used by the orchestrator.",
    )


class AgentRunResponse(BaseModel):
    """Run status response."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: RunStatus
    prompt: str
    project_name: str
    working_directory: str
    plan_file: str
    agent_success: bool | None = None
    final_summary: str | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    status_url: str | None = None


class AgentRunListResponse(BaseModel):
    """Response model for run listing."""

    model_config = ConfigDict(extra="forbid")

    items: list[AgentRunResponse]


class HealthResponse(BaseModel):
    """Health-check payload."""

    model_config = ConfigDict(extra="forbid")

    status: str
    service: str
    timestamp: datetime
    total_runs: int
    active_runs: int
