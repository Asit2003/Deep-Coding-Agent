"""Executable entrypoint for the FastAPI service."""

from __future__ import annotations

import os

import uvicorn


def _get_int_env(name: str, default: int) -> int:
    """Parse an integer environment variable with fallback."""
    raw_value = os.getenv(name, str(default)).strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def main() -> None:
    """Run the FastAPI application with Uvicorn."""
    host = os.getenv("AGENT_API_HOST", "0.0.0.0").strip() or "0.0.0.0"
    port = _get_int_env("AGENT_API_PORT", 8000)
    reload_enabled = os.getenv("AGENT_API_RELOAD", "false").strip().lower() == "true"
    log_level = os.getenv("AGENT_API_LOG_LEVEL", "info").strip().lower() or "info"

    uvicorn.run(
        "agent_api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload_enabled,
        log_level=log_level,
    )


if __name__ == "__main__":
    main()
