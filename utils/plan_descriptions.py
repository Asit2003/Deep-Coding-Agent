"""Detailed descriptions for planning tools used by the coding agent."""

PLAN_USAGE_INSTRUCTIONS = """Use these tools to manage multi-step implementation plans.

Recommended workflow:
1. Break down the request with decompose_task().
2. Create persistent plan state with create_plan().
3. Refine target outcomes with set_subgoals().
4. Keep step state current with update_plan().
5. Record execution progress with track_progress().
6. Capture lessons and close the loop with reflect_on_plan().
"""

CREATE_PLAN_DESCRIPTION = """Create a new markdown-backed execution plan.

Parameters:
- task (required)
- steps (required)
- plan_file (optional, default='agent_plan.md')
- overwrite (optional, default=False)

Creates plan state in a markdown file under the workspace."""

UPDATE_PLAN_DESCRIPTION = """Update status for one step in an existing plan.

Parameters:
- step_number (required, 1-based index)
- status (required: pending|in_progress|completed|blocked)
- note (optional)
- plan_file (optional, default='agent_plan.md')

Updates step status and optionally appends a progress note."""

DECOMPOSE_TASK_DESCRIPTION = """Break a task string into actionable steps.

Parameters:
- task (required)
- max_steps (optional, default=6)

Returns a list of concise implementation steps."""

SET_SUBGOALS_DESCRIPTION = """Set or append subgoals for the current plan.

Parameters:
- subgoals (required)
- plan_file (optional, default='agent_plan.md')
- replace (optional, default=True)

Stores explicit subgoals to guide implementation quality."""

TRACK_PROGRESS_DESCRIPTION = """Append progress updates and optionally
finalize the plan.

Parameters:
- message (required)
- percent_complete (optional, 0..100)
- plan_file (optional, default='agent_plan.md')
- complete_plan (optional, default=False)
- cleanup_plan_file (optional, default=False)

Use cleanup_plan_file=True when work is complete and plan state can be removed."""

REFLECT_ON_PLAN_DESCRIPTION = """Record a short reflection for the current plan.

Parameters:
- summary (required)
- risks (optional)
- next_actions (optional)
- plan_file (optional, default='agent_plan.md')
- finalize (optional, default=False)
- cleanup_plan_file (optional, default=False)

Supports end-of-task reflection and optional plan cleanup."""

__all__ = [
    "PLAN_USAGE_INSTRUCTIONS",
    "CREATE_PLAN_DESCRIPTION",
    "UPDATE_PLAN_DESCRIPTION",
    "DECOMPOSE_TASK_DESCRIPTION",
    "SET_SUBGOALS_DESCRIPTION",
    "TRACK_PROGRESS_DESCRIPTION",
    "REFLECT_ON_PLAN_DESCRIPTION",
]
