"""Todo-style plan inspection tools built on markdown-backed plan state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from utils import plans as plan_ops


def _load_plan_state(plan_file: str) -> dict[str, Any] | None:
    """Load embedded JSON state from a plan markdown file."""
    path = Path(plan_file)
    if not path.exists() or not path.is_file():
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None

    match = plan_ops.STATE_PATTERN.search(content)
    if match is None:
        return None
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


@tool(parse_docstring=False)
def get_plan_overview(plan_file: str = plan_ops.DEFAULT_PLAN_FILE) -> dict[str, Any]:
    """Return high-level metadata for the current plan file.

    Args:
        plan_file: Markdown plan file path.
    """
    state = _load_plan_state(plan_file)
    if state is None:
        return {"error": f"Unable to load plan state from '{plan_file}'"}
    return {
        "task": state.get("task", ""),
        "status": state.get("status", ""),
        "percent_complete": state.get("percent_complete"),
        "num_steps": len(state.get("steps", [])),
        "num_subgoals": len(state.get("subgoals", [])),
        "updated_at": state.get("updated_at", ""),
    }


@tool(parse_docstring=False)
def get_open_steps(plan_file: str = plan_ops.DEFAULT_PLAN_FILE) -> list[dict[str, Any]]:
    """List all steps that are not completed.

    Args:
        plan_file: Markdown plan file path.
    """
    state = _load_plan_state(plan_file)
    if state is None:
        return [{"error": f"Unable to load plan state from '{plan_file}'"}]

    steps = state.get("steps", [])
    open_steps = [
        {
            "id": int(item.get("id", 0)),
            "description": str(item.get("description", "")).strip(),
            "status": str(item.get("status", "")).strip(),
        }
        for item in steps
        if str(item.get("status", "")).strip() != "completed"
    ]
    return open_steps


@tool(parse_docstring=False)
def mark_step_completed(
    step_number: int,
    note: str = "",
    plan_file: str = plan_ops.DEFAULT_PLAN_FILE,
) -> str:
    """Mark a specific plan step as completed.

    Args:
        step_number: 1-based step index.
        note: Optional progress note.
        plan_file: Markdown plan file path.
    """
    return plan_ops.update_plan(
        step_number=step_number,
        status="completed",
        note=note,
        plan_file=plan_file,
    )


@tool(parse_docstring=False)
def mark_step_blocked(
    step_number: int,
    note: str,
    plan_file: str = plan_ops.DEFAULT_PLAN_FILE,
) -> str:
    """Mark a specific plan step as blocked.

    Args:
        step_number: 1-based step index.
        note: Required reason for the blocked state.
        plan_file: Markdown plan file path.
    """
    return plan_ops.update_plan(
        step_number=step_number,
        status="blocked",
        note=note,
        plan_file=plan_file,
    )


__all__ = [
    "get_plan_overview",
    "get_open_steps",
    "mark_step_completed",
    "mark_step_blocked",
]
