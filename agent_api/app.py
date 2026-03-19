"""Application factory for the Deep Coding Agent API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agent_api.logging import configure_logging
from agent_api.routers import health, runs
from agent_api.service import AgentRunManager


def create_app(run_manager: AgentRunManager | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging()

    managed_run_manager = run_manager or AgentRunManager()
    should_shutdown_manager = run_manager is None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.run_manager = managed_run_manager
        yield
        if should_shutdown_manager:
            managed_run_manager.shutdown()

    app = FastAPI(
        title="Deep Coding Agent API",
        version="0.1.0",
        description=(
            "HTTP API for submitting coding-agent runs and tracking their status."
        ),
        lifespan=lifespan,
    )

    @app.get("/", tags=["meta"])
    def root() -> dict[str, str]:
        return {
            "service": "deep-coding-agent-api",
            "docs_url": "/docs",
            "health_url": "/health",
        }

    app.include_router(health.router)
    app.include_router(runs.router)
    return app
