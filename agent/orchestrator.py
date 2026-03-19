"""Deep Agents orchestrator for coding requests."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_openai import ChatOpenAI

from agent.prompts import DEEP_AGENT_SYSTEM_PROMPT
from agent.state import AgentState, PlanTask
from agent.test_builder import TestRunner
from config import AgentConfig, settings
from tools.plan_tools import (
    create_plan,
    decompose_task,
    reflect_on_plan,
    set_subgoals,
    track_progress,
    update_plan,
)
from tools.research_tools import (
    list_reference_docs,
    search_project_context,
    search_reference_notes,
)
from tools.shell_tools import make_run_shell_tool
from tools.todo_tools import (
    get_open_steps,
    get_plan_overview,
    mark_step_blocked,
    mark_step_completed,
)
from utils import files as file_ops
from utils import plans as plan_ops

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


def _slugify_project_name(value: str) -> str:
    """Normalize project name text into a filesystem-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        return "app"
    parts = [part for part in slug.split("-") if part]
    return "-".join(parts[:5]) or "app"


def _normalize_projects_root(value: str) -> str:
    """Normalize configured projects root into workspace-relative POSIX path."""
    normalized = value.strip().replace("\\", "/").strip("/")
    return normalized or "project"


_REQUEST_STOP_WORDS = {
    "add",
    "a",
    "an",
    "and",
    "app",
    "application",
    "build",
    "can",
    "create",
    "develop",
    "docs",
    "documentation",
    "for",
    "generate",
    "help",
    "implement",
    "in",
    "into",
    "make",
    "my",
    "new",
    "of",
    "on",
    "please",
    "project",
    "setup",
    "tests",
    "test",
    "the",
    "to",
    "with",
    "write",
    "you",
    "your",
}
_TYPE_KEYWORDS = {"api", "backend", "frontend", "cli", "library", "service"}
_NON_DOMAIN_WORDS = {"endpoint", "feature", "system", "workflow"}
_FRAMEWORK_TO_TYPE = {
    "fastapi": "api",
    "flask": "api",
    "django": "api",
    "react": "frontend",
    "nextjs": "frontend",
    "next": "frontend",
    "vue": "frontend",
    "angular": "frontend",
}


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _extract_for_phrase_tokens(text: str) -> list[str]:
    match = re.search(r"\bfor\s+([a-zA-Z0-9 _-]{2,120})", text, flags=re.IGNORECASE)
    if not match:
        return []
    phrase = match.group(1)
    phrase = re.split(
        r"\b(?:with|using|including|that|which|and|to|in)\b",
        phrase,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return re.findall(r"[a-zA-Z0-9]+", phrase.lower())


def _detect_project_type(words: list[str]) -> str | None:
    for word in words:
        if word in _TYPE_KEYWORDS:
            return word
    for word in words:
        mapped = _FRAMEWORK_TO_TYPE.get(word)
        if mapped:
            return mapped
    if "endpoint" in words:
        return "api"
    return None


def _domain_tokens(words: list[str]) -> list[str]:
    framework_names = set(_FRAMEWORK_TO_TYPE.keys())
    return [
        word
        for word in words
        if word not in _REQUEST_STOP_WORDS
        and word not in _TYPE_KEYWORDS
        and word not in _NON_DOMAIN_WORDS
        and word not in framework_names
        and len(word) > 1
    ]


def build_project_root(projects_root: str, project_name: str) -> str:
    """Build the effective project directory path."""
    normalized_root = _normalize_projects_root(projects_root)
    normalized_project = _slugify_project_name(project_name)
    return f"{normalized_root}/{normalized_project}"


def derive_project_name(user_request: str) -> str:
    """Derive a project name hint from user request text."""
    text = " ".join(user_request.split()).strip()
    if not text:
        return "app"

    pattern_matchers = [
        r"project(?:\s+name)?\s*[:=-]\s*[\"']?([a-zA-Z0-9 _-]{2,80})",
        r"project\s+(?:named|called)\s+[\"']?([a-zA-Z0-9 _-]{2,80})",
        r"create\s+(?:a|an)?\s*(?:new)?\s*([a-zA-Z0-9 _-]{2,80})\s+project",
    ]
    for pattern in pattern_matchers:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _slugify_project_name(match.group(1))

    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    if not words:
        return "app"
    project_type = _detect_project_type(words)

    prioritized = _extract_for_phrase_tokens(text)
    core_tokens = _domain_tokens(prioritized) if prioritized else []
    if not core_tokens:
        core_tokens = _domain_tokens(words)

    if project_type and core_tokens:
        type_for_pattern = rf"\b{re.escape(project_type)}\b\s+for\b"
        if re.search(type_for_pattern, text, flags=re.IGNORECASE):
            ordered_tokens = [project_type] + [
                token for token in core_tokens if token != project_type
            ]
            return _slugify_project_name(
                "-".join(_dedupe_preserve_order(ordered_tokens[:4]))
            )

    if project_type and project_type not in core_tokens:
        core_tokens.append(project_type)

    if not core_tokens and project_type:
        core_tokens = [project_type]
    if not core_tokens:
        return "app"

    return _slugify_project_name("-".join(_dedupe_preserve_order(core_tokens[:4])))


def partition_tasks(tasks: list[PlanTask]) -> tuple[list[int], list[int]]:
    """Split plan tasks into independent and dependent task IDs."""
    independent: list[int] = []
    dependent: list[int] = []

    for task in sorted(tasks, key=lambda item: int(item.get("id", 0))):
        task_id = int(task.get("id", 0))
        if task_id <= 0:
            continue
        depends_on = [int(dep) for dep in task.get("depends_on", []) if int(dep) > 0]
        if depends_on:
            dependent.append(task_id)
        else:
            independent.append(task_id)
    return independent, dependent


def merge_task_results(
    tasks: list[PlanTask],
    results: list[dict[str, Any]],
) -> tuple[list[PlanTask], dict[str, str], list[int], list[int]]:
    """Merge execution results into task objects and aggregate status IDs."""
    result_by_id: dict[int, dict[str, Any]] = {}
    for result in results:
        task_id = int(result.get("task_id", 0))
        if task_id > 0:
            result_by_id[task_id] = result

    merged: list[PlanTask] = []
    task_results: dict[str, str] = {}
    completed_ids: list[int] = []
    failed_ids: list[int] = []

    for task in sorted(tasks, key=lambda item: int(item.get("id", 0))):
        task_copy: PlanTask = dict(task)
        task_id = int(task_copy.get("id", 0))
        payload = result_by_id.get(task_id)
        if payload:
            status = str(payload.get("status", "pending")).strip().lower()
            if status not in {
                "pending",
                "in_progress",
                "completed",
                "failed",
                "blocked",
            }:
                status = "pending"
            task_copy["status"] = status
            summary = str(payload.get("summary", "")).strip()
            if summary:
                task_copy["result"] = summary
                task_results[str(task_id)] = summary
            files_touched = payload.get("files_touched")
            if isinstance(files_touched, list):
                normalized_files = [str(item).strip() for item in files_touched]
                task_copy["files_touched"] = [path for path in normalized_files if path]

        status_value = str(task_copy.get("status", "pending")).strip().lower()
        if status_value == "completed":
            completed_ids.append(task_id)
        elif status_value in {"failed", "blocked"}:
            failed_ids.append(task_id)

        merged.append(task_copy)

    return (
        merged,
        task_results,
        sorted(set(completed_ids)),
        sorted(set(failed_ids)),
    )


def _extract_text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        chunks: list[str] = []
        for block in content:
            if isinstance(block, str):
                chunks.append(block.strip())
            elif isinstance(block, dict):
                text = str(block.get("text", "")).strip()
                if text:
                    chunks.append(text)
        return "\n".join(part for part in chunks if part).strip()
    return str(content).strip()


def _extract_final_assistant_summary(payload: dict[str, Any]) -> str:
    messages = payload.get("messages", [])
    if not isinstance(messages, list):
        return ""

    for message in reversed(messages):
        role = ""
        content: Any = ""
        if isinstance(message, dict):
            role = str(message.get("role", "")).strip().lower()
            content = message.get("content", "")
        else:
            role = str(getattr(message, "type", "")).strip().lower()
            content = getattr(message, "content", "")

        if role in {"assistant", "ai"}:
            text = _extract_text_from_content(content)
            if text:
                return text
    return ""


@dataclass
class CodingOrchestrator:
    """OpenAI-only orchestrator powered by LangChain Deep Agents."""

    config: AgentConfig | None = None
    graph: Any | None = field(default=None, init=False)
    test_runner: TestRunner = field(init=False)

    def __post_init__(self) -> None:
        self.config = self.config or settings
        self.test_runner = TestRunner(self.config)

    def _default_project_root(self) -> str:
        return build_project_root(str(self.config.projects_root), "app")

    def _build_deep_agent(self, project_root: str) -> Any:
        model = ChatOpenAI(
            model=str(self.config.model_name),
            api_key=str(self.config.api_key),
            base_url=str(self.config.base_url),
            temperature=float(self.config.temperature),
        )

        backend = FilesystemBackend(
            root_dir=(WORKSPACE_ROOT / project_root).resolve(),
            virtual_mode=True,
        )

        run_shell = make_run_shell_tool(base_directory=project_root)
        custom_tools = [
            create_plan,
            update_plan,
            decompose_task,
            set_subgoals,
            track_progress,
            reflect_on_plan,
            get_plan_overview,
            get_open_steps,
            mark_step_completed,
            mark_step_blocked,
            list_reference_docs,
            search_reference_notes,
            search_project_context,
            run_shell,
        ]
        return create_deep_agent(
            model=model,
            backend=backend,
            tools=custom_tools,
            system_prompt=DEEP_AGENT_SYSTEM_PROMPT,
            name="deep-coding-agent",
        )

    def _build_user_prompt(
        self,
        user_request: str,
        project_name: str,
        project_root: str,
    ) -> str:
        return "\n".join(
            [
                f"User request: {user_request}",
                f"Project name: {project_name}",
                f"Project root: {project_root}",
                f"Plan file: {self.config.plan_file}",
                "",
                "Execution requirements:",
                f"- Implement code changes under {project_root}.",
                "- Use plan tools to keep plan state accurate while working.",
                "- Keep naming concise and concept-based.",
                "- Follow language conventions (PEP 8 for Python).",
                "- Add/update tests when behavior changes.",
                "- Summarize what changed and what remains at the end.",
            ]
        )

    def run(self, user_request: str, project_name: str | None = None) -> AgentState:
        """Invoke Deep Agents workflow for a user request."""
        normalized_request = user_request.strip()
        verify_result = plan_ops.verify_plan_file(
            task=normalized_request,
            plan_file=str(self.config.plan_file),
            max_steps=int(self.config.planning_max_steps),
        )
        if verify_result.startswith("Error:"):
            return {
                "user_request": normalized_request,
                "project_name": (project_name or "").strip(),
                "plan_file": str(self.config.plan_file),
                "final_summary": f"Plan preflight failed: {verify_result}",
            }

        if not str(self.config.api_key or "").strip():
            return {
                "user_request": normalized_request,
                "project_name": (project_name or "").strip(),
                "plan_file": str(self.config.plan_file),
                "final_summary": "Execution blocked: OPENAI_API_KEY is not configured.",
            }

        raw_project_name = str(project_name or "").strip()
        resolved_project_name = _slugify_project_name(
            raw_project_name or derive_project_name(normalized_request)
        )
        project_root = build_project_root(
            str(self.config.projects_root),
            resolved_project_name,
        )

        make_result = file_ops.make_directory(
            path=project_root,
            parents=True,
            exist_ok=True,
        )
        if str(make_result).startswith("Error:"):
            return {
                "user_request": normalized_request,
                "project_name": resolved_project_name,
                "project_root": project_root,
                "plan_file": str(self.config.plan_file),
                "final_summary": f"Execution blocked: {make_result}",
            }

        if self.graph is None:
            try:
                self.graph = self._build_deep_agent(project_root=project_root)
            except Exception as err:  # noqa: BLE001
                return {
                    "user_request": normalized_request,
                    "project_name": resolved_project_name,
                    "project_root": project_root,
                    "plan_file": str(self.config.plan_file),
                    "final_summary": f"Failed to initialize Deep Agent: {err}",
                }

        invoke_payload = {
            "messages": [
                {
                    "role": "user",
                    "content": self._build_user_prompt(
                        user_request=normalized_request,
                        project_name=resolved_project_name,
                        project_root=project_root,
                    ),
                }
            ]
        }

        try:
            agent_state = self.graph.invoke(invoke_payload)
        except Exception as err:  # noqa: BLE001
            return {
                "user_request": normalized_request,
                "project_name": resolved_project_name,
                "project_root": project_root,
                "plan_file": str(self.config.plan_file),
                "final_summary": f"Deep Agent execution failed: {err}",
            }

        state_payload = agent_state if isinstance(agent_state, dict) else {}
        agent_summary = _extract_final_assistant_summary(state_payload)
        if not agent_summary:
            agent_summary = "(Deep Agent returned no textual summary.)"

        tests_result = self.test_runner.run()
        tests_passed = bool(tests_result.get("passed", False))
        tests_exit_code = int(tests_result.get("exit_code", -1))
        tests_output = str(tests_result.get("output", "")).strip()

        final_summary = "\n".join(
            [
                f"Request: {normalized_request}",
                f"Project root: {project_root}",
                f"Plan file: {self.config.plan_file}",
                f"Tests passed: {tests_passed}",
                f"Tests exit code: {tests_exit_code}",
                "Agent summary:",
                agent_summary,
            ]
        )
        return {
            "user_request": normalized_request,
            "project_name": resolved_project_name,
            "project_root": project_root,
            "plan_file": str(self.config.plan_file),
            "tests_passed": tests_passed,
            "tests_exit_code": tests_exit_code,
            "tests_output": tests_output,
            "final_summary": final_summary,
        }

    def invoke(self, user_request: str, project_name: str | None = None) -> AgentState:
        """Alias to `run()` for API ergonomics."""
        return self.run(user_request, project_name=project_name)


def main() -> None:
    """CLI entrypoint for the Deep Agents orchestrator."""
    parser = argparse.ArgumentParser(
        description="Run the OpenAI Deep Agents coding orchestrator."
    )
    parser.add_argument("request", help="Problem statement for the coding agent.")
    parser.add_argument(
        "--project-name",
        default="",
        help=(
            "Optional output project directory name under configured "
            "AGENT_PROJECTS_ROOT."
        ),
    )
    args = parser.parse_args()

    orchestrator = CodingOrchestrator()
    result = orchestrator.run(args.request, project_name=args.project_name)
    print(result.get("final_summary", "(no summary generated)"))


if __name__ == "__main__":
    main()
