"""FastAPI dependency helpers."""

from __future__ import annotations

from fastapi import Request

from agent_api.service import AgentRunManager


def get_run_manager(request: Request) -> AgentRunManager:
    """Return the shared run manager from app state."""
    return request.app.state.run_manager
