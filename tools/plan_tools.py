"""LangChain tool bindings for planning operations.

All concrete planning logic lives in `utils/plans.py`. This module exposes
those functions as `@tool` instances with detailed descriptions.
"""

from typing import Any

from langchain_core.tools import tool

from utils import plans as plan_ops
from utils.plan_descriptions import (
    CREATE_PLAN_DESCRIPTION,
    DECOMPOSE_TASK_DESCRIPTION,
    PLAN_USAGE_INSTRUCTIONS,
    REFLECT_ON_PLAN_DESCRIPTION,
    SET_SUBGOALS_DESCRIPTION,
    TRACK_PROGRESS_DESCRIPTION,
    UPDATE_PLAN_DESCRIPTION,
)

_TOOL_SPECS = [
    ("create_plan", CREATE_PLAN_DESCRIPTION),
    ("update_plan", UPDATE_PLAN_DESCRIPTION),
    ("decompose_task", DECOMPOSE_TASK_DESCRIPTION),
    ("set_subgoals", SET_SUBGOALS_DESCRIPTION),
    ("track_progress", TRACK_PROGRESS_DESCRIPTION),
    ("reflect_on_plan", REFLECT_ON_PLAN_DESCRIPTION),
]

for _name, _description in _TOOL_SPECS:
    globals()[_name] = tool(description=_description, parse_docstring=False)(
        getattr(plan_ops, _name)
    )


def make_scoped_plan_tools(plan_file: str) -> list[Any]:
    """Build plan tools bound to one concrete plan file."""

    @tool("create_plan", description=CREATE_PLAN_DESCRIPTION, parse_docstring=False)
    def _create_plan(
        task: str,
        steps: list[str] | None = None,
        overwrite: bool = False,
    ) -> str:
        return plan_ops.create_plan(
            task=task,
            steps=steps,
            plan_file=plan_file,
            overwrite=overwrite,
        )

    @tool("update_plan", description=UPDATE_PLAN_DESCRIPTION, parse_docstring=False)
    def _update_plan(
        step_number: int,
        status: str,
        note: str = "",
    ) -> str:
        return plan_ops.update_plan(
            step_number=step_number,
            status=status,
            note=note,
            plan_file=plan_file,
        )

    @tool(
        "decompose_task",
        description=DECOMPOSE_TASK_DESCRIPTION,
        parse_docstring=False,
    )
    def _decompose_task(task: str, max_steps: int = 6) -> list[str]:
        return plan_ops.decompose_task(task=task, max_steps=max_steps)

    @tool("set_subgoals", description=SET_SUBGOALS_DESCRIPTION, parse_docstring=False)
    def _set_subgoals(subgoals: list[str], replace: bool = True) -> str:
        return plan_ops.set_subgoals(
            subgoals=subgoals,
            plan_file=plan_file,
            replace=replace,
        )

    @tool(
        "track_progress",
        description=TRACK_PROGRESS_DESCRIPTION,
        parse_docstring=False,
    )
    def _track_progress(
        message: str,
        percent_complete: int | None = None,
        complete_plan: bool = False,
        cleanup_plan_file: bool = False,
    ) -> str:
        return plan_ops.track_progress(
            message=message,
            percent_complete=percent_complete,
            plan_file=plan_file,
            complete_plan=complete_plan,
            cleanup_plan_file=cleanup_plan_file,
        )

    @tool(
        "reflect_on_plan",
        description=REFLECT_ON_PLAN_DESCRIPTION,
        parse_docstring=False,
    )
    def _reflect_on_plan(
        summary: str,
        risks: list[str] | None = None,
        next_actions: list[str] | None = None,
        finalize: bool = False,
        cleanup_plan_file: bool = False,
    ) -> str:
        return plan_ops.reflect_on_plan(
            summary=summary,
            risks=risks,
            next_actions=next_actions,
            plan_file=plan_file,
            finalize=finalize,
            cleanup_plan_file=cleanup_plan_file,
        )

    return [
        _create_plan,
        _update_plan,
        _decompose_task,
        _set_subgoals,
        _track_progress,
        _reflect_on_plan,
    ]


__all__ = [
    "PLAN_USAGE_INSTRUCTIONS",
    "make_scoped_plan_tools",
    *[name for name, _ in _TOOL_SPECS],
]
