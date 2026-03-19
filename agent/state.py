"""Typed state models used across the LangGraph orchestration flow."""

from __future__ import annotations

from typing import Literal, TypedDict

TaskStatus = Literal["pending", "in_progress", "completed", "failed", "blocked"]


class PlanTask(TypedDict, total=False):
    """One planned coding task with optional dependency metadata."""

    id: int
    description: str
    depends_on: list[int]
    status: TaskStatus
    result: str
    files_touched: list[str]


class AgentState(TypedDict, total=False):
    """Top-level graph state shared by all orchestration nodes."""

    user_request: str
    project_name: str
    project_root: str
    plan_file: str

    plan_tasks: list[PlanTask]
    independent_task_ids: list[int]
    dependent_task_ids: list[int]

    task_results: dict[str, str]
    completed_task_ids: list[int]
    failed_task_ids: list[int]

    verifier_report: str
    verifier_approved: bool
    reviewer_issues: list[str]

    tests_output: str
    tests_passed: bool
    tests_exit_code: int

    iteration: int
    max_iterations: int
    final_summary: str
