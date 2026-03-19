"""Runtime configuration for the Deep Coding Agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class AgentConfig:
    """Dataclass-backed app configuration loaded from `.env` and env vars."""

    provider: str | None = None
    model_name: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    temperature: float | None = None
    planning_max_steps: int | None = None
    max_tool_rounds: int | None = None
    max_graph_iterations: int | None = None
    max_parallel_tasks: int | None = None
    projects_root: str | None = None
    plan_file: str | None = None
    run_tests_command: str | None = None

    def __post_init__(self) -> None:
        load_dotenv(Path(__file__).resolve().with_name(".env"), override=False)

        # OpenAI-only runtime mode.
        provider = "openai"
        model_default = "gpt-5-mini"
        model_name = (
            self.model_name
            if self.model_name is not None
            else os.getenv("OPENAI_MODEL", model_default)
        )
        model_name = model_name.strip() or model_default

        if self.api_key is not None:
            api_key = self.api_key.strip()
        else:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()

        base_url_default = "https://api.openai.com/v1"
        base_url = (
            self.base_url
            if self.base_url is not None
            else os.getenv("OPENAI_BASE_URL", base_url_default)
        )
        base_url = base_url.strip() or base_url_default

        if self.temperature is None:
            raw_temperature = os.getenv("AGENT_TEMPERATURE", "0.1").strip()
            try:
                temperature = float(raw_temperature) if raw_temperature else 0.1
            except ValueError:
                temperature = 0.1
        else:
            temperature = float(self.temperature)

        if self.planning_max_steps is None:
            raw_planning = os.getenv("PLANNING_MAX_STEPS", "8").strip()
            try:
                planning_max_steps = int(raw_planning) if raw_planning else 8
            except ValueError:
                planning_max_steps = 8
        else:
            planning_max_steps = int(self.planning_max_steps)
        planning_max_steps = max(1, planning_max_steps)

        if self.max_tool_rounds is None:
            raw_tool_rounds = os.getenv("MAX_TOOL_ROUNDS", "10").strip()
            try:
                max_tool_rounds = int(raw_tool_rounds) if raw_tool_rounds else 10
            except ValueError:
                max_tool_rounds = 10
        else:
            max_tool_rounds = int(self.max_tool_rounds)
        max_tool_rounds = max(1, max_tool_rounds)

        if self.max_graph_iterations is None:
            raw_graph_iterations = os.getenv("MAX_GRAPH_ITERATIONS", "2").strip()
            try:
                max_graph_iterations = (
                    int(raw_graph_iterations) if raw_graph_iterations else 2
                )
            except ValueError:
                max_graph_iterations = 2
        else:
            max_graph_iterations = int(self.max_graph_iterations)
        max_graph_iterations = max(1, max_graph_iterations)

        if self.max_parallel_tasks is None:
            raw_parallel_tasks = os.getenv("MAX_PARALLEL_TASKS", "3").strip()
            try:
                max_parallel_tasks = (
                    int(raw_parallel_tasks) if raw_parallel_tasks else 3
                )
            except ValueError:
                max_parallel_tasks = 3
        else:
            max_parallel_tasks = int(self.max_parallel_tasks)
        max_parallel_tasks = max(1, max_parallel_tasks)

        projects_root = (
            self.projects_root
            if self.projects_root is not None
            else os.getenv("AGENT_PROJECTS_ROOT", "project")
        )
        projects_root = projects_root.strip().replace("\\", "/").strip("/") or "project"

        plan_file = (
            self.plan_file
            if self.plan_file is not None
            else os.getenv("AGENT_PLAN_FILE", "agent_plan.md")
        )
        plan_file = plan_file.strip() or "agent_plan.md"

        run_tests_command = (
            self.run_tests_command
            if self.run_tests_command is not None
            else os.getenv("AGENT_TEST_COMMAND", "uv run pytest -q")
        )
        run_tests_command = run_tests_command.strip() or "uv run pytest -q"

        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "model_name", model_name)
        object.__setattr__(self, "api_key", api_key)
        object.__setattr__(self, "base_url", base_url)
        object.__setattr__(self, "temperature", temperature)
        object.__setattr__(self, "planning_max_steps", planning_max_steps)
        object.__setattr__(self, "max_tool_rounds", max_tool_rounds)
        object.__setattr__(self, "max_graph_iterations", max_graph_iterations)
        object.__setattr__(self, "max_parallel_tasks", max_parallel_tasks)
        object.__setattr__(self, "projects_root", projects_root)
        object.__setattr__(self, "plan_file", plan_file)
        object.__setattr__(self, "run_tests_command", run_tests_command)


settings = AgentConfig()

__all__ = ["AgentConfig", "settings"]
