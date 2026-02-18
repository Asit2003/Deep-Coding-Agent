"""Planning utilities with markdown-backed persistent state."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN_FILE = "agent_plan.md"
VALID_STATUSES = {"pending", "in_progress", "completed", "blocked"}

STATE_START = "<!-- PLAN_STATE_JSON_START -->"
STATE_END = "<!-- PLAN_STATE_JSON_END -->"
STATE_PATTERN = re.compile(
    rf"{re.escape(STATE_START)}\s*```json\s*(\{{.*\}})\s*```"
    rf"\s*{re.escape(STATE_END)}",
    flags=re.DOTALL,
)


def _resolve_workspace_path(path_value: str) -> Path:
    """Resolve a path and reject traversal outside the workspace root."""
    raw_path = Path(path_value).expanduser()
    resolved = (
        raw_path.resolve()
        if raw_path.is_absolute()
        else (WORKSPACE_ROOT / raw_path).resolve()
    )
    try:
        resolved.relative_to(WORKSPACE_ROOT)
    except ValueError as err:
        raise ValueError(
            f"Path '{path_value}' is outside workspace root "
            f"'{WORKSPACE_ROOT.as_posix()}'"
        ) from err
    return resolved


def _to_workspace_relative(path: Path) -> str:
    """Render a path relative to workspace root."""
    return path.relative_to(WORKSPACE_ROOT).as_posix()


def _now_utc_iso() -> str:
    """Return timezone-aware UTC timestamp."""
    return datetime.now(tz=timezone.utc).isoformat()


def _normalize_text_items(values: list[str] | None) -> list[str]:
    """Normalize text entries and drop duplicates while preserving order."""
    if not values:
        return []

    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        text = str(raw).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _build_plan_items(
    items: list[str], default_status: str = "pending"
) -> list[dict[str, Any]]:
    """Build normalized checklist item objects."""
    return [
        {"id": idx, "description": text, "status": default_status}
        for idx, text in enumerate(items, start=1)
    ]


def _coerce_item_list(raw_items: Any) -> list[dict[str, Any]]:
    """Normalize arbitrary list-like plan items into stable shape."""
    if not isinstance(raw_items, list):
        return []

    items: list[dict[str, Any]] = []
    for raw in raw_items:
        if isinstance(raw, dict):
            description = str(raw.get("description", "")).strip()
            status = str(raw.get("status", "pending")).strip()
        else:
            description = str(raw).strip()
            status = "pending"

        if not description:
            continue
        if status not in VALID_STATUSES:
            status = "pending"

        items.append({"description": description, "status": status})

    return [
        {"id": idx, "description": item["description"], "status": item["status"]}
        for idx, item in enumerate(items, start=1)
    ]


def _coerce_progress(raw_progress: Any) -> list[dict[str, Any]]:
    """Normalize persisted progress entries."""
    if not isinstance(raw_progress, list):
        return []

    progress: list[dict[str, Any]] = []
    for entry in raw_progress:
        if not isinstance(entry, dict):
            continue
        message = str(entry.get("message", "")).strip()
        timestamp = str(entry.get("timestamp", "")).strip() or _now_utc_iso()
        percent = entry.get("percent_complete")
        if not message:
            continue
        if not isinstance(percent, int):
            percent = None
        progress.append(
            {
                "timestamp": timestamp,
                "message": message,
                "percent_complete": percent,
            }
        )
    return progress


def _coerce_reflections(raw_reflections: Any) -> list[dict[str, Any]]:
    """Normalize persisted reflection entries."""
    if not isinstance(raw_reflections, list):
        return []

    reflections: list[dict[str, Any]] = []
    for entry in raw_reflections:
        if not isinstance(entry, dict):
            continue
        summary = str(entry.get("summary", "")).strip()
        timestamp = str(entry.get("timestamp", "")).strip() or _now_utc_iso()
        if not summary:
            continue
        risks = _normalize_text_items(entry.get("risks"))
        next_actions = _normalize_text_items(entry.get("next_actions"))
        reflections.append(
            {
                "timestamp": timestamp,
                "summary": summary,
                "risks": risks,
                "next_actions": next_actions,
            }
        )
    return reflections


def _coerce_state(raw_state: dict[str, Any]) -> dict[str, Any]:
    """Coerce loaded state to expected structure."""
    created_at = str(raw_state.get("created_at", "")).strip() or _now_utc_iso()
    updated_at = str(raw_state.get("updated_at", "")).strip() or created_at
    status = str(raw_state.get("status", "active")).strip() or "active"
    if status not in {"active", "completed"}:
        status = "active"

    percent_complete = raw_state.get("percent_complete")
    if not isinstance(percent_complete, int):
        percent_complete = None
    elif percent_complete < 0 or percent_complete > 100:
        percent_complete = None

    return {
        "task": str(raw_state.get("task", "")).strip(),
        "status": status,
        "created_at": created_at,
        "updated_at": updated_at,
        "percent_complete": percent_complete,
        "steps": _coerce_item_list(raw_state.get("steps")),
        "subgoals": _coerce_item_list(raw_state.get("subgoals")),
        "progress_log": _coerce_progress(raw_state.get("progress_log")),
        "reflections": _coerce_reflections(raw_state.get("reflections")),
    }


def _format_items(items: list[dict[str, Any]]) -> str:
    """Render checklist items for markdown view."""
    if not items:
        return "- (none)"

    lines: list[str] = []
    for item in items:
        status = str(item.get("status", "pending"))
        checked = "x" if status == "completed" else " "
        lines.append(
            f"{item.get('id', 0)}. [{checked}] ({status}) {item.get('description', '')}"
        )
    return "\n".join(lines)


def _format_progress(entries: list[dict[str, Any]]) -> str:
    """Render progress timeline for markdown view."""
    if not entries:
        return "- (none)"

    lines: list[str] = []
    for entry in entries:
        percent = entry.get("percent_complete")
        percent_label = f"{percent}%" if isinstance(percent, int) else "-"
        lines.append(
            f"- {entry.get('timestamp', '')} | {percent_label} | "
            f"{entry.get('message', '')}"
        )
    return "\n".join(lines)


def _format_reflections(reflections: list[dict[str, Any]]) -> str:
    """Render reflection section for markdown view."""
    if not reflections:
        return "- (none)"

    lines: list[str] = []
    for idx, reflection in enumerate(reflections, start=1):
        lines.append(f"### Reflection {idx} ({reflection.get('timestamp', '')})")
        lines.append(reflection.get("summary", ""))

        risks = reflection.get("risks", [])
        if risks:
            lines.append("Risks:")
            lines.extend(f"- {risk}" for risk in risks)

        next_actions = reflection.get("next_actions", [])
        if next_actions:
            lines.append("Next Actions:")
            lines.extend(f"- {action}" for action in next_actions)

    return "\n".join(lines)


def _serialize_markdown(state: dict[str, Any]) -> str:
    """Serialize plan state to a readable markdown document."""
    percent = state.get("percent_complete")
    percent_label = f"{percent}%" if isinstance(percent, int) else "n/a"

    lines = [
        "# Agent Plan",
        "",
        "## Summary",
        f"- Task: {state.get('task', '')}",
        f"- Status: {state.get('status', 'active')}",
        f"- Progress: {percent_label}",
        f"- Created (UTC): {state.get('created_at', '')}",
        f"- Updated (UTC): {state.get('updated_at', '')}",
        "",
        "## Steps",
        _format_items(state.get("steps", [])),
        "",
        "## Subgoals",
        _format_items(state.get("subgoals", [])),
        "",
        "## Progress Log",
        _format_progress(state.get("progress_log", [])),
        "",
        "## Reflections",
        _format_reflections(state.get("reflections", [])),
        "",
        "---",
        STATE_START,
        "```json",
        json.dumps(state, indent=2, sort_keys=True),
        "```",
        STATE_END,
        "",
    ]
    return "\n".join(lines)


def _load_state_from_markdown(content: str) -> dict[str, Any]:
    """Extract JSON state from markdown content."""
    match = STATE_PATTERN.search(content)
    if not match:
        raise ValueError("Plan file is missing embedded JSON state markers")

    try:
        loaded = json.loads(match.group(1))
    except json.JSONDecodeError as err:
        raise ValueError(f"Plan file contains invalid JSON state: {err}") from err

    if not isinstance(loaded, dict):
        raise ValueError("Plan state must be a JSON object")
    return _coerce_state(loaded)


def _write_state(plan_path: Path, state: dict[str, Any]) -> str:
    """Persist state into markdown file."""
    try:
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(_serialize_markdown(state), encoding="utf-8")
        return f"Saved plan to {_to_workspace_relative(plan_path)}"
    except OSError as err:
        return f"Error: Unable to write plan file '{plan_path.as_posix()}': {err}"


def _read_existing_state(
    plan_file: str,
) -> tuple[Path | None, dict[str, Any] | None, str]:
    """Load state from plan file and return path, state, and error."""
    try:
        plan_path = _resolve_workspace_path(plan_file)
    except ValueError as err:
        return None, None, f"Error: {err}"

    if not plan_path.exists():
        return plan_path, None, f"Error: Plan file '{plan_file}' not found"
    if not plan_path.is_file():
        return plan_path, None, f"Error: '{plan_file}' is not a file"

    try:
        content = plan_path.read_text(encoding="utf-8")
    except OSError as err:
        return plan_path, None, f"Error: Unable to read '{plan_file}': {err}"

    try:
        state = _load_state_from_markdown(content)
    except ValueError as err:
        return plan_path, None, f"Error: {err}"
    return plan_path, state, ""


def _recompute_percent_from_steps(state: dict[str, Any]) -> None:
    """Recompute completion percentage from plan steps."""
    steps = state.get("steps", [])
    if not steps:
        state["percent_complete"] = 0
        return

    completed = sum(1 for item in steps if item.get("status") == "completed")
    state["percent_complete"] = int(round((completed / len(steps)) * 100))


def _mark_all_completed(items: list[dict[str, Any]]) -> None:
    """Mark every item in a checklist as completed."""
    for item in items:
        item["status"] = "completed"


def _maybe_cleanup_plan_file(
    *,
    plan_path: Path,
    cleanup_plan_file: bool,
    state: dict[str, Any],
) -> str | None:
    """Delete plan file when requested and state is completed."""
    if not cleanup_plan_file:
        return None
    if state.get("status") != "completed":
        return "Error: cleanup_plan_file requires a completed plan"

    try:
        plan_path.unlink(missing_ok=True)
        return f"Completed plan and removed {_to_workspace_relative(plan_path)}"
    except OSError as err:
        return (
            "Warning: Plan completed but cleanup failed for "
            f"'{_to_workspace_relative(plan_path)}': {err}"
        )


def create_plan(
    task: str,
    steps: list[str] | None = None,
    plan_file: str = DEFAULT_PLAN_FILE,
    overwrite: bool = False,
) -> str:
    """Create a markdown-backed plan file for a task."""
    task_text = task.strip()
    if not task_text:
        return "Error: task must not be empty"

    normalized_steps = _normalize_text_items(steps)
    if not normalized_steps:
        normalized_steps = decompose_task(task_text)
        if normalized_steps and normalized_steps[0].startswith("Error:"):
            return normalized_steps[0]

    try:
        plan_path = _resolve_workspace_path(plan_file)
    except ValueError as err:
        return f"Error: {err}"

    if plan_path.exists() and not overwrite:
        return f"Error: Plan file '{plan_file}' already exists and overwrite is False"
    if plan_path.exists() and plan_path.is_dir():
        return f"Error: '{plan_file}' is a directory"

    created_at = _now_utc_iso()
    state: dict[str, Any] = {
        "task": task_text,
        "status": "active",
        "created_at": created_at,
        "updated_at": created_at,
        "percent_complete": 0,
        "steps": _build_plan_items(normalized_steps),
        "subgoals": [],
        "progress_log": [
            {
                "timestamp": created_at,
                "message": "Plan created",
                "percent_complete": 0,
            }
        ],
        "reflections": [],
    }
    if state["steps"]:
        state["steps"][0]["status"] = "in_progress"

    write_result = _write_state(plan_path, state)
    if write_result.startswith("Error:"):
        return write_result

    return (
        f"Created plan {_to_workspace_relative(plan_path)} with "
        f"{len(state['steps'])} step(s)"
    )


def update_plan(
    step_number: int,
    status: str,
    note: str = "",
    plan_file: str = DEFAULT_PLAN_FILE,
) -> str:
    """Update one plan step status and persist changes."""
    if step_number < 1:
        return "Error: step_number must be >= 1"
    if status not in VALID_STATUSES:
        return (
            "Error: status must be one of: pending, in_progress, completed, blocked"
        )

    plan_path, state, error = _read_existing_state(plan_file)
    if error:
        return error
    if not state or not plan_path:
        return "Error: Unable to load plan state"

    steps = state.get("steps", [])
    if not steps:
        return "Error: Plan has no steps to update"
    if step_number > len(steps):
        return (
            f"Error: step_number {step_number} is out of range "
            f"(1..{len(steps)})"
        )

    if status == "in_progress":
        for idx, item in enumerate(steps, start=1):
            if idx != step_number and item.get("status") == "in_progress":
                item["status"] = "pending"

    target = steps[step_number - 1]
    target["status"] = status

    timestamp = _now_utc_iso()
    if note.strip():
        state.setdefault("progress_log", []).append(
            {
                "timestamp": timestamp,
                "message": note.strip(),
                "percent_complete": None,
            }
        )

    if steps and all(item.get("status") == "completed" for item in steps):
        state["status"] = "completed"
    else:
        state["status"] = "active"

    state["updated_at"] = timestamp
    _recompute_percent_from_steps(state)

    write_result = _write_state(plan_path, state)
    if write_result.startswith("Error:"):
        return write_result

    return (
        f"Updated step {step_number} to '{status}' in "
        f"{_to_workspace_relative(plan_path)}"
    )


def decompose_task(task: str, max_steps: int = 6) -> list[str]:
    """Decompose task text into ordered implementation steps."""
    if max_steps <= 0:
        return ["Error: max_steps must be > 0"]

    normalized = " ".join(task.split()).strip()
    if not normalized:
        return ["Error: task must not be empty"]

    candidates: list[str] = []
    for sentence in re.split(r"[;\n.]+", normalized):
        for part in re.split(r"\b(?:then|after that|next)\b", sentence, flags=re.I):
            cleaned = part.strip(" ,:-")
            if cleaned:
                candidates.append(cleaned)

    if len(candidates) < 2 and "," in normalized:
        for part in normalized.split(","):
            cleaned = part.strip(" ,:-")
            if cleaned:
                candidates.append(cleaned)

    unique_candidates = _normalize_text_items(candidates)
    if len(unique_candidates) >= 2:
        return unique_candidates[:max_steps]

    return [
        f"Clarify acceptance criteria for: {normalized}",
        "Inspect the relevant code and dependencies",
        "Implement the required code changes",
        "Validate behavior with tests and checks",
        "Summarize results and remaining follow-ups",
    ][:max_steps]


def set_subgoals(
    subgoals: list[str],
    plan_file: str = DEFAULT_PLAN_FILE,
    replace: bool = True,
) -> str:
    """Set or append subgoals in the persisted plan state."""
    normalized_subgoals = _normalize_text_items(subgoals)
    if not normalized_subgoals:
        return "Error: subgoals must include at least one non-empty item"

    plan_path, state, error = _read_existing_state(plan_file)
    if error:
        return error
    if not state or not plan_path:
        return "Error: Unable to load plan state"

    current_subgoals = state.get("subgoals", [])
    status_by_description = {
        item.get("description", ""): item.get("status", "pending")
        for item in current_subgoals
    }

    if replace:
        merged = normalized_subgoals
    else:
        merged = _normalize_text_items(
            [item.get("description", "") for item in current_subgoals]
            + normalized_subgoals
        )

    updated_subgoals: list[dict[str, Any]] = []
    for idx, description in enumerate(merged, start=1):
        existing_status = status_by_description.get(description, "pending")
        if existing_status not in VALID_STATUSES:
            existing_status = "pending"
        updated_subgoals.append(
            {"id": idx, "description": description, "status": existing_status}
        )

    state["subgoals"] = updated_subgoals
    state["updated_at"] = _now_utc_iso()

    write_result = _write_state(plan_path, state)
    if write_result.startswith("Error:"):
        return write_result

    action = "Set" if replace else "Updated"
    return (
        f"{action} {len(updated_subgoals)} subgoal(s) in "
        f"{_to_workspace_relative(plan_path)}"
    )


def track_progress(
    message: str,
    percent_complete: int | None = None,
    plan_file: str = DEFAULT_PLAN_FILE,
    complete_plan: bool = False,
    cleanup_plan_file: bool = False,
) -> str:
    """Append progress entry, update completion, and optionally cleanup plan file."""
    note = message.strip()
    if not note:
        return "Error: message must not be empty"
    if percent_complete is not None and (
        percent_complete < 0 or percent_complete > 100
    ):
        return "Error: percent_complete must be between 0 and 100"

    plan_path, state, error = _read_existing_state(plan_file)
    if error:
        return error
    if not state or not plan_path:
        return "Error: Unable to load plan state"

    timestamp = _now_utc_iso()
    state.setdefault("progress_log", []).append(
        {
            "timestamp": timestamp,
            "message": note,
            "percent_complete": percent_complete,
        }
    )

    if percent_complete is not None:
        state["percent_complete"] = percent_complete

    if complete_plan or percent_complete == 100:
        _mark_all_completed(state.get("steps", []))
        _mark_all_completed(state.get("subgoals", []))
        state["status"] = "completed"
        state["percent_complete"] = 100
    else:
        if state.get("steps") and all(
            item.get("status") == "completed" for item in state["steps"]
        ):
            state["status"] = "completed"
        else:
            state["status"] = "active"
        if percent_complete is None:
            _recompute_percent_from_steps(state)

    state["updated_at"] = timestamp

    write_result = _write_state(plan_path, state)
    if write_result.startswith("Error:"):
        return write_result

    cleanup_result = _maybe_cleanup_plan_file(
        plan_path=plan_path,
        cleanup_plan_file=cleanup_plan_file,
        state=state,
    )
    if cleanup_result:
        return cleanup_result

    return (
        f"Logged progress in {_to_workspace_relative(plan_path)} "
        f"(status={state.get('status')}, progress={state.get('percent_complete')}%)"
    )


def reflect_on_plan(
    summary: str,
    risks: list[str] | None = None,
    next_actions: list[str] | None = None,
    plan_file: str = DEFAULT_PLAN_FILE,
    finalize: bool = False,
    cleanup_plan_file: bool = False,
) -> str:
    """Add a reflection entry and optionally finalize or cleanup the plan."""
    summary_text = summary.strip()
    if not summary_text:
        return "Error: summary must not be empty"

    plan_path, state, error = _read_existing_state(plan_file)
    if error:
        return error
    if not state or not plan_path:
        return "Error: Unable to load plan state"

    timestamp = _now_utc_iso()
    reflection = {
        "timestamp": timestamp,
        "summary": summary_text,
        "risks": _normalize_text_items(risks),
        "next_actions": _normalize_text_items(next_actions),
    }
    state.setdefault("reflections", []).append(reflection)

    if finalize:
        _mark_all_completed(state.get("steps", []))
        _mark_all_completed(state.get("subgoals", []))
        state["status"] = "completed"
        state["percent_complete"] = 100
    else:
        _recompute_percent_from_steps(state)

    state["updated_at"] = timestamp

    write_result = _write_state(plan_path, state)
    if write_result.startswith("Error:"):
        return write_result

    cleanup_result = _maybe_cleanup_plan_file(
        plan_path=plan_path,
        cleanup_plan_file=cleanup_plan_file,
        state=state,
    )
    if cleanup_result:
        return cleanup_result

    return (
        f"Recorded reflection in {_to_workspace_relative(plan_path)} "
        f"(total reflections={len(state.get('reflections', []))})"
    )
