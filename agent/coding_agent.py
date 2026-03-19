"""Deep coding agent with iterative tool-calling execution."""

from __future__ import annotations

from collections.abc import Callable
import json
import posixpath
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from agent.prompts import CODER_SYSTEM_PROMPT, CODER_USER_PROMPT
from agent.state import PlanTask
from config import AgentConfig
from utils import files as file_ops
from utils import plans as plan_ops
from utils import shell as shell_ops

ToolFn = Callable[..., Any]


@dataclass(frozen=True)
class ToolBinding:
    """One callable tool and its OpenAI function-calling schema."""

    name: str
    description: str
    parameters: dict[str, Any]
    fn: ToolFn


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    """Extract and parse the first JSON object found in a string."""
    text = raw_text.strip()
    if not text:
        return None

    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL | re.I)
        if match:
            text = match.group(1).strip()

    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        text = match.group(0)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _safe_json_dumps(value: Any) -> str:
    """Serialize any value for tool-message transport."""
    try:
        return json.dumps(value, ensure_ascii=True)
    except (TypeError, ValueError):
        return json.dumps(str(value), ensure_ascii=True)


def _scope_project_path(path_value: str, project_root: str) -> str:
    """Scope a relative path under the task project root."""
    root_input = project_root.replace("\\", "/").strip()
    root = posixpath.normpath(root_input or ".")
    if root in {"", "/"}:
        root = "."

    raw = str(path_value).strip().replace("\\", "/")
    if root == ".":
        if raw in {"", ".", "./"}:
            scoped = "."
        else:
            trimmed = raw.lstrip("/").removeprefix("./")
            scoped = trimmed or "."
    else:
        if raw in {"", ".", "./"}:
            scoped = root
        elif raw.startswith(f"{root}/") or raw == root:
            scoped = raw
        else:
            trimmed = raw.lstrip("/").removeprefix("./")
            scoped = f"{root}/{trimmed}" if trimmed else root

    normalized = posixpath.normpath(scoped)
    if normalized in {"", ".", ".."} or normalized.startswith("../"):
        raise ValueError(f"Invalid path '{path_value}'")
    if root != "." and not (normalized == root or normalized.startswith(f"{root}/")):
        raise ValueError(f"Path '{path_value}' must stay within '{root}'")
    return normalized


@dataclass
class DeepCodingAgent:
    """Coding worker that executes one task through iterative tool use."""

    config: AgentConfig

    def _build_client(self) -> OpenAI | None:
        if not self.config.api_key:
            return None
        return OpenAI(api_key=self.config.api_key, base_url=self.config.base_url)

    def _build_tool_bindings(self, project_root: str) -> dict[str, ToolBinding]:
        plan_file = self.config.plan_file

        def _update_plan(**kwargs: Any) -> str:
            payload = dict(kwargs)
            payload.setdefault("plan_file", plan_file)
            return plan_ops.update_plan(**payload)

        def _track_progress(**kwargs: Any) -> str:
            payload = dict(kwargs)
            payload.setdefault("plan_file", plan_file)
            return plan_ops.track_progress(**payload)

        def _scope_or_error(path_value: str) -> str:
            return _scope_project_path(path_value, project_root)

        def _write_file(
            file_path: str,
            content: str,
            overwrite: bool = True,
            create_dirs: bool = True,
        ) -> str:
            scoped = _scope_or_error(file_path)
            return file_ops.write_file(
                file_path=scoped,
                content=content,
                overwrite=overwrite,
                create_dirs=create_dirs,
            )

        def _append_file(file_path: str, content: str, create_dirs: bool = True) -> str:
            scoped = _scope_or_error(file_path)
            return file_ops.append_file(
                file_path=scoped,
                content=content,
                create_dirs=create_dirs,
            )

        def _replace_in_file(
            file_path: str, old: str, new: str, count: int = -1
        ) -> str:
            scoped = _scope_or_error(file_path)
            return file_ops.replace_in_file(
                file_path=scoped,
                old=old,
                new=new,
                count=count,
            )

        def _make_directory(
            path: str, parents: bool = True, exist_ok: bool = True
        ) -> str:
            scoped = _scope_or_error(path)
            return file_ops.make_directory(
                path=scoped,
                parents=parents,
                exist_ok=exist_ok,
            )

        def _run_shell(
            command: list[str],
            cwd: str = ".",
            timeout_seconds: int = shell_ops.DEFAULT_TIMEOUT_SECONDS,
        ) -> dict[str, Any]:
            return shell_ops.run_shell_command(
                args=command,
                cwd=cwd,
                base_directory=project_root,
                timeout_seconds=timeout_seconds,
            )

        bindings = [
            ToolBinding(
                name="list_files",
                description="List direct entries in a directory.",
                parameters={
                    "type": "object",
                    "properties": {"directory": {"type": "string", "default": "."}},
                },
                fn=file_ops.list_files,
            ),
            ToolBinding(
                name="safe_list_files",
                description="Safely list repository files recursively.",
                parameters={
                    "type": "object",
                    "properties": {
                        "directory": {"type": "string", "default": "."},
                        "max_file_size": {"type": "integer", "default": 100000},
                        "include_hidden": {"type": "boolean", "default": False},
                    },
                },
                fn=file_ops.safe_list_files,
            ),
            ToolBinding(
                name="read_file",
                description="Read a UTF-8 file by path.",
                parameters={
                    "type": "object",
                    "properties": {"file_path": {"type": "string"}},
                    "required": ["file_path"],
                },
                fn=file_ops.read_file,
            ),
            ToolBinding(
                name="read_file_lines",
                description="Read selected lines from a UTF-8 file.",
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "start": {"type": "integer", "default": 1},
                        "end": {"type": "integer"},
                    },
                    "required": ["file_path"],
                },
                fn=file_ops.read_file_lines,
            ),
            ToolBinding(
                name="search_in_files",
                description="Search text across the repository.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "root": {"type": "string", "default": "."},
                        "case_sensitive": {"type": "boolean", "default": False},
                        "max_results": {"type": "integer", "default": 50},
                    },
                    "required": ["query"],
                },
                fn=file_ops.search_in_files,
            ),
            ToolBinding(
                name="write_file",
                description="Create or overwrite a UTF-8 file.",
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": (
                                f"Path inside project root '{project_root}'."
                            ),
                        },
                        "content": {"type": "string"},
                        "overwrite": {"type": "boolean", "default": True},
                        "create_dirs": {"type": "boolean", "default": True},
                    },
                    "required": ["file_path", "content"],
                },
                fn=_write_file,
            ),
            ToolBinding(
                name="append_file",
                description="Append text to a UTF-8 file.",
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": (
                                f"Path inside project root '{project_root}'."
                            ),
                        },
                        "content": {"type": "string"},
                        "create_dirs": {"type": "boolean", "default": True},
                    },
                    "required": ["file_path", "content"],
                },
                fn=_append_file,
            ),
            ToolBinding(
                name="replace_in_file",
                description="Replace existing text content in a file.",
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": (
                                f"Path inside project root '{project_root}'."
                            ),
                        },
                        "old": {"type": "string"},
                        "new": {"type": "string"},
                        "count": {"type": "integer", "default": -1},
                    },
                    "required": ["file_path", "old", "new"],
                },
                fn=_replace_in_file,
            ),
            ToolBinding(
                name="make_directory",
                description="Create a directory path.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (f"Directory path inside '{project_root}'."),
                        },
                        "parents": {"type": "boolean", "default": True},
                        "exist_ok": {"type": "boolean", "default": True},
                    },
                    "required": ["path"],
                },
                fn=_make_directory,
            ),
            ToolBinding(
                name="run_shell",
                description=(
                    "Run an allowlisted non-interactive command inside the project "
                    "root. Allowed command families are python/py, pytest, uv run, "
                    "ruff, and read-only git subcommands."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Command tokens, e.g. ['uv', 'run', 'pytest', '-q']."
                            ),
                        },
                        "cwd": {
                            "type": "string",
                            "default": ".",
                            "description": (
                                f"Working directory inside '{project_root}'."
                            ),
                        },
                        "timeout_seconds": {
                            "type": "integer",
                            "default": shell_ops.DEFAULT_TIMEOUT_SECONDS,
                        },
                    },
                    "required": ["command"],
                },
                fn=_run_shell,
            ),
            ToolBinding(
                name="update_plan",
                description="Update plan step status by number.",
                parameters={
                    "type": "object",
                    "properties": {
                        "step_number": {"type": "integer"},
                        "status": {"type": "string"},
                        "note": {"type": "string", "default": ""},
                        "plan_file": {"type": "string", "default": plan_file},
                    },
                    "required": ["step_number", "status"],
                },
                fn=_update_plan,
            ),
            ToolBinding(
                name="track_progress",
                description="Append a progress note to current plan.",
                parameters={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "percent_complete": {"type": "integer"},
                        "plan_file": {"type": "string", "default": plan_file},
                    },
                    "required": ["message"],
                },
                fn=_track_progress,
            ),
        ]
        return {item.name: item for item in bindings}

    def _invoke_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        bindings: dict[str, ToolBinding],
    ) -> Any:
        binding = bindings.get(tool_name)
        if binding is None:
            return f"Error: unknown tool '{tool_name}'"
        try:
            return binding.fn(**arguments)
        except TypeError as err:
            return f"Error: invalid arguments for '{tool_name}': {err}"
        except Exception as err:  # noqa: BLE001 - protect loop from tool crashes.
            return f"Error: tool '{tool_name}' failed: {err}"

    @staticmethod
    def _parse_result_payload(raw_text: str) -> tuple[str, str, list[str]]:
        payload = _extract_json_object(raw_text)
        if payload is None:
            summary = raw_text.strip() or "Task finished without structured summary."
            return "completed", summary, []

        status = str(payload.get("status", "completed")).strip().lower() or "completed"
        if status not in {"completed", "failed", "blocked"}:
            status = "completed"

        summary = str(payload.get("summary", "")).strip()
        if not summary:
            summary = "Task finished without summary."

        files_raw = payload.get("files_touched")
        files_touched = []
        if isinstance(files_raw, list):
            for item in files_raw:
                path = str(item).strip()
                if path and path not in files_touched:
                    files_touched.append(path)
        return status, summary, files_touched

    def execute_task(
        self,
        task: PlanTask,
        dependency_context: dict[str, str] | None = None,
        *,
        project_name: str = "",
        project_root: str = "project/app",
    ) -> dict[str, Any]:
        """Execute one task with tool-calling and return structured status."""
        task_id = int(task.get("id", 0))
        description = str(task.get("description", "")).strip()
        depends_on = [int(item) for item in task.get("depends_on", []) if int(item) > 0]
        dependency_context = dependency_context or {}

        if task_id <= 0 or not description:
            return {
                "task_id": task_id,
                "status": "failed",
                "summary": "Invalid task payload",
                "files_touched": [],
                "tool_events": [],
            }

        plan_ops.update_plan(
            step_number=task_id,
            status="in_progress",
            note=f"Started task {task_id}: {description}",
            plan_file=self.config.plan_file,
        )

        client = self._build_client()
        if client is None:
            key_name = (
                "GEMINI_API_KEY"
                if str(self.config.provider).strip().lower() == "gemini"
                else "OPENAI_API_KEY"
            )
            summary = f"No {key_name} configured for coding execution."
            plan_ops.update_plan(
                step_number=task_id,
                status="blocked",
                note=summary,
                plan_file=self.config.plan_file,
            )
            plan_ops.track_progress(message=summary, plan_file=self.config.plan_file)
            return {
                "task_id": task_id,
                "status": "blocked",
                "summary": summary,
                "files_touched": [],
                "tool_events": [],
            }

        bindings = self._build_tool_bindings(project_root=project_root)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": binding.name,
                    "description": binding.description,
                    "parameters": binding.parameters,
                },
            }
            for binding in bindings.values()
        ]

        dep_context_lines = []
        for dep_id in depends_on:
            summary = dependency_context.get(str(dep_id), "(missing summary)")
            dep_context_lines.append(f"- Task {dep_id}: {summary}")
        dep_context = "\n".join(dep_context_lines) if dep_context_lines else "- (none)"

        user_prompt = CODER_USER_PROMPT.format(
            project_name=project_name or "app",
            project_root=project_root,
            task_id=task_id,
            description=description,
            depends_on=depends_on or [],
            dependency_context=dep_context,
        )
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": CODER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        tool_events: list[str] = []
        final_text = ""

        for _ in range(self.config.max_tool_rounds):
            try:
                response = client.chat.completions.create(
                    model=self.config.model_name,
                    # temperature=self.config.temperature,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
            except Exception as err:  # noqa: BLE001 - provider/network variability.
                final_text = json.dumps(
                    {
                        "status": "failed",
                        "summary": f"Coding model call failed: {err}",
                        "files_touched": [],
                    }
                )
                break

            message = response.choices[0].message
            tool_calls = message.tool_calls or []

            assistant_payload: dict[str, Any] = {
                "role": "assistant",
                "content": message.content or "",
            }
            if tool_calls:
                assistant_payload["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments or "{}",
                        },
                    }
                    for call in tool_calls
                ]
            messages.append(assistant_payload)

            if not tool_calls:
                final_text = message.content or ""
                break

            for call in tool_calls:
                args_raw = call.function.arguments or "{}"
                try:
                    args = json.loads(args_raw)
                except json.JSONDecodeError:
                    args = {}
                if not isinstance(args, dict):
                    args = {}

                tool_result = self._invoke_tool(
                    tool_name=call.function.name,
                    arguments=args,
                    bindings=bindings,
                )
                tool_events.append(f"{call.function.name}({args})")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.function.name,
                        "content": _safe_json_dumps(tool_result),
                    }
                )

        if not final_text:
            final_text = json.dumps(
                {
                    "status": "failed",
                    "summary": "Model loop exhausted before final response.",
                    "files_touched": [],
                }
            )

        status, summary, files_touched = self._parse_result_payload(final_text)
        plan_status = "completed" if status == "completed" else "blocked"

        plan_ops.update_plan(
            step_number=task_id,
            status=plan_status,
            note=summary,
            plan_file=self.config.plan_file,
        )
        plan_ops.track_progress(
            message=f"Task {task_id} -> {status}: {summary}",
            plan_file=self.config.plan_file,
        )

        return {
            "task_id": task_id,
            "status": status,
            "summary": summary,
            "files_touched": files_touched,
            "tool_events": tool_events,
        }

    def execute_tasks(
        self,
        tasks: list[PlanTask],
        dependency_context: dict[str, str] | None = None,
        *,
        project_name: str = "",
        project_root: str = "project/app",
    ) -> list[dict[str, Any]]:
        """Execute a batch of tasks concurrently."""
        if not tasks:
            return []

        dependency_context = dependency_context or {}
        ordered_tasks = sorted(tasks, key=lambda item: int(item.get("id", 0)))
        workers = max(1, min(self.config.max_parallel_tasks, len(ordered_tasks)))
        if workers == 1:
            return [
                self.execute_task(
                    task,
                    dependency_context,
                    project_name=project_name,
                    project_root=project_root,
                )
                for task in ordered_tasks
            ]

        results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    self.execute_task,
                    task,
                    dependency_context,
                    project_name=project_name,
                    project_root=project_root,
                ): int(task.get("id", 0))
                for task in ordered_tasks
            }
            for future in as_completed(futures):
                task_id = futures[future]
                try:
                    payload = future.result()
                except Exception as err:  # noqa: BLE001 - keep batch robust.
                    payload = {
                        "task_id": task_id,
                        "status": "failed",
                        "summary": f"Worker failed: {err}",
                        "files_touched": [],
                        "tool_events": [],
                    }
                results.append(payload)

        results.sort(key=lambda item: int(item.get("task_id", 0)))
        return results
