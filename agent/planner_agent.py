"""Planner agent that converts user intent + HLD into executable tasks."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from agent.prompts import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT
from agent.state import PlanTask
from config import AgentConfig
from utils import files as file_ops
from utils import plans as plan_ops


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    """Extract and parse the first JSON object found in a string."""
    if not raw_text.strip():
        return None

    candidate = raw_text.strip()
    if candidate.startswith("```"):
        code_fence_match = re.search(
            r"```(?:json)?\s*(\{.*\})\s*```",
            candidate,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if code_fence_match:
            candidate = code_fence_match.group(1).strip()

    if not candidate.startswith("{"):
        json_match = re.search(r"\{.*\}", candidate, flags=re.DOTALL)
        if not json_match:
            return None
        candidate = json_match.group(0)

    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _normalize_dependencies(task_id: int, raw_depends_on: Any) -> list[int]:
    """Normalize dependency IDs and keep only valid previous tasks."""
    if not isinstance(raw_depends_on, list):
        return []

    deps: list[int] = []
    seen: set[int] = set()
    for value in raw_depends_on:
        try:
            dep_id = int(value)
        except (TypeError, ValueError):
            continue
        if dep_id <= 0 or dep_id >= task_id or dep_id in seen:
            continue
        seen.add(dep_id)
        deps.append(dep_id)
    return deps


def _coerce_tasks(raw_tasks: Any, fallback_steps: list[str]) -> list[PlanTask]:
    """Coerce model JSON output into stable `PlanTask` records."""
    tasks: list[PlanTask] = []
    if isinstance(raw_tasks, list):
        for idx, raw_task in enumerate(raw_tasks, start=1):
            if isinstance(raw_task, dict):
                description = str(raw_task.get("description", "")).strip()
                depends_on = _normalize_dependencies(idx, raw_task.get("depends_on"))
            else:
                description = str(raw_task).strip()
                depends_on = []
            if not description:
                continue
            tasks.append(
                {
                    "id": idx,
                    "description": description,
                    "depends_on": depends_on,
                    "status": "pending",
                }
            )

    if tasks:
        return tasks

    return [
        {
            "id": idx,
            "description": step,
            "depends_on": [] if idx == 1 else [idx - 1],
            "status": "pending",
        }
        for idx, step in enumerate(fallback_steps, start=1)
    ]


@dataclass
class PlannerAgent:
    """Planner that generates persisted task plans for the orchestrator."""

    config: AgentConfig

    def _build_client(self) -> OpenAI | None:
        if not self.config.api_key:
            return None
        return OpenAI(api_key=self.config.api_key, base_url=self.config.base_url)

    def _build_project_context(self) -> str:
        listing = file_ops.safe_list_files(
            directory=".",
            max_file_size=50_000,
            include_hidden=False,
        )
        if listing and listing[0].startswith("Error:"):
            return listing[0]
        preview = listing[:150]
        return "\n".join(f"- {path}" for path in preview) or "- (no files found)"

    def _default_project_root(self) -> str:
        normalized_root = (
            str(self.config.projects_root or "project")
            .strip()
            .replace("\\", "/")
            .strip("/")
        )
        if not normalized_root:
            normalized_root = "project"
        return f"{normalized_root}/app"

    def build_plan(
        self,
        user_request: str,
        project_root: str | None = None,
    ) -> dict[str, Any]:
        """Generate a dependency-aware plan and persist it to markdown."""
        request = user_request.strip()
        if not request:
            return {
                "plan_tasks": [],
                "create_plan_result": "Error: user request must not be empty",
                "set_subgoals_result": "Skipped",
            }
        resolved_project_root = (
            (project_root or "").strip().replace("\\", "/").strip("/")
        ) or self._default_project_root()

        fallback_steps = plan_ops.decompose_task(
            request, max_steps=self.config.planning_max_steps
        )
        if fallback_steps and fallback_steps[0].startswith("Error:"):
            fallback_steps = [
                "Inspect the relevant repository context",
                "Implement the required code changes",
                "Run tests and validate behavior",
            ]

        payload: dict[str, Any] = {}
        client = self._build_client()
        if client is not None:
            prompt = PLANNER_USER_PROMPT.format(
                user_request=request,
                project_root=resolved_project_root,
                project_context=self._build_project_context(),
            )
            try:
                response = client.chat.completions.create(
                    model=self.config.model_name,
                    # temperature=self.config.temperature,
                    messages=[
                        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                )
                content = response.choices[0].message.content or ""
                payload = _extract_json_object(content) or {}
            except Exception as err:  # noqa: BLE001 - provider/network variability.
                payload = {"error": f"Planner model call failed: {err}"}

        tasks = _coerce_tasks(payload.get("tasks"), fallback_steps)
        plan_steps = [task["description"] for task in tasks]

        create_result = plan_ops.create_plan(
            task=request,
            steps=plan_steps,
            plan_file=self.config.plan_file,
            overwrite=True,
        )
        subgoal_candidates = payload.get("subgoals")
        if not isinstance(subgoal_candidates, list) or not subgoal_candidates:
            subgoal_candidates = plan_steps[: min(4, len(plan_steps))]
        set_subgoals_result = plan_ops.set_subgoals(
            subgoals=[
                str(item).strip() for item in subgoal_candidates if str(item).strip()
            ],
            plan_file=self.config.plan_file,
            replace=True,
        )

        return {
            "plan_tasks": tasks,
            "create_plan_result": create_result,
            "set_subgoals_result": set_subgoals_result,
        }
