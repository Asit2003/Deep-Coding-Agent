"""Reviewer agent for post-implementation verification."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from agent.prompts import REVIEWER_SYSTEM_PROMPT, REVIEWER_USER_PROMPT
from agent.state import PlanTask
from config import AgentConfig


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    """Extract and parse first JSON object from model text output."""
    text = raw_text.strip()
    if not text:
        return None

    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL | re.I)
        if match:
            text = match.group(1).strip()

    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        text = match.group(0)

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


@dataclass
class ReviewerAgent:
    """Evaluate execution quality and produce approval decision."""

    config: AgentConfig

    def _build_client(self) -> OpenAI | None:
        if not self.config.api_key:
            return None
        return OpenAI(api_key=self.config.api_key, base_url=self.config.base_url)

    def _fallback_review(self, tasks: list[PlanTask]) -> dict[str, Any]:
        failed = [
            int(task.get("id", 0))
            for task in tasks
            if str(task.get("status", "")).strip() in {"failed", "blocked"}
        ]
        if failed:
            return {
                "approved": False,
                "summary": f"Tasks {failed} are not completed.",
                "issues": [f"Task {task_id} requires follow-up" for task_id in failed],
                "next_actions": ["Re-run failed tasks and verify outputs"],
            }
        return {
            "approved": True,
            "summary": "All tasks are marked completed.",
            "issues": [],
            "next_actions": [],
        }

    def review(
        self,
        user_request: str,
        tasks: list[PlanTask],
        task_results: dict[str, str],
        tests_output: str = "",
    ) -> dict[str, Any]:
        """Produce a verification report from task outcomes."""
        client = self._build_client()
        if client is None:
            return self._fallback_review(tasks)

        prompt = REVIEWER_USER_PROMPT.format(
            user_request=user_request.strip(),
            task_results=json.dumps(
                {
                    "tasks": tasks,
                    "task_results": task_results,
                },
                indent=2,
                ensure_ascii=True,
            ),
            tests_output=(tests_output or "(tests not run yet)")[:7000],
        )
        try:
            response = client.chat.completions.create(
                model=self.config.model_name,
                # temperature=self.config.temperature,
                messages=[
                    {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content or ""
            payload = _extract_json_object(content)
            if payload is None:
                fallback = self._fallback_review(tasks)
                fallback["summary"] = (
                    f"{fallback['summary']} Reviewer returned unstructured output."
                )
                return fallback
        except Exception as err:  # noqa: BLE001 - provider/network variability.
            fallback = self._fallback_review(tasks)
            fallback["summary"] = f"{fallback['summary']} Reviewer call failed: {err}"
            return fallback

        approved = bool(payload.get("approved", False))
        summary = str(payload.get("summary", "")).strip() or "No summary provided."
        issues_raw = payload.get("issues")
        actions_raw = payload.get("next_actions")
        issues = [str(item).strip() for item in issues_raw or [] if str(item).strip()]
        next_actions = [
            str(item).strip() for item in actions_raw or [] if str(item).strip()
        ]
        return {
            "approved": approved,
            "summary": summary,
            "issues": issues,
            "next_actions": next_actions,
        }
