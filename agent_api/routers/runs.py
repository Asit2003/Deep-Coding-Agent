"""Run submission and status routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from agent_api.dependencies import get_run_manager
from agent_api.schemas import (
    AgentRunCreateRequest,
    AgentRunListResponse,
    AgentRunResponse,
)
from agent_api.service import AgentRunManager, RunNotFoundError

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])
RunManagerDependency = Annotated[AgentRunManager, Depends(get_run_manager)]


def _attach_status_url(
    request: Request, response: AgentRunResponse
) -> AgentRunResponse:
    """Attach a self status URL to a run response."""
    response.status_url = str(request.url_for("get_run", run_id=response.run_id))
    return response


@router.post(
    "/runs",
    response_model=AgentRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_run(
    payload: AgentRunCreateRequest,
    request: Request,
    run_manager: RunManagerDependency,
) -> AgentRunResponse:
    """Queue a new agent run."""
    try:
        record = run_manager.submit(payload)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        ) from err

    response = record.to_response(include_result=False)
    return _attach_status_url(request, response)


@router.get("/runs/{run_id}", response_model=AgentRunResponse, name="get_run")
def get_run(
    run_id: str,
    request: Request,
    run_manager: RunManagerDependency,
) -> AgentRunResponse:
    """Fetch the latest status for a queued or completed run."""
    try:
        record = run_manager.get(run_id)
    except RunNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err

    response = record.to_response(include_result=True)
    return _attach_status_url(request, response)


@router.get("/runs", response_model=AgentRunListResponse)
def list_runs(
    request: Request,
    run_manager: RunManagerDependency,
    limit: int = Query(default=20, ge=1, le=100),
) -> AgentRunListResponse:
    """List recent runs in reverse chronological order."""
    items = [
        _attach_status_url(request, record.to_response(include_result=False))
        for record in run_manager.list_runs(limit=limit)
    ]
    return AgentRunListResponse(items=items)
