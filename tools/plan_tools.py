"""LangChain tool bindings for planning operations.

All concrete planning logic lives in `utils/plans.py`. This module exposes
those functions as `@tool` instances with detailed descriptions.
"""

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
    globals()[_name] = tool(description=_description, parse_docstring=True)(
        getattr(plan_ops, _name)
    )


__all__ = ["PLAN_USAGE_INSTRUCTIONS", *[name for name, _ in _TOOL_SPECS]]

