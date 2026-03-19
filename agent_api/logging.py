"""Logging configuration for the FastAPI service."""

from __future__ import annotations

import logging
import os

_CONFIGURED = False


def configure_logging() -> None:
    """Configure process-wide logging once."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = os.getenv("AGENT_API_LOG_LEVEL", "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    _CONFIGURED = True
