from pathlib import Path
from types import SimpleNamespace

from agent.planner_agent import PlannerAgent
from config import AgentConfig


def test_planner_fallback_generates_tasks_and_plan_file() -> None:
    plan_file = "tmp_plan_planner_fallback.md"
    path = Path(plan_file)
    try:
        config = AgentConfig(
            api_key="",
            plan_file=plan_file,
            planning_max_steps=4,
        )
        planner = PlannerAgent(config)
        result = planner.build_plan(
            user_request="Inspect code then implement agent graph then run tests",
        )

        assert not result["create_plan_result"].startswith("Error:")
        assert isinstance(result["plan_tasks"], list)
        assert len(result["plan_tasks"]) >= 2
        assert path.exists()
    finally:
        if path.exists():
            try:
                path.unlink()
            except PermissionError:
                pass


class _FakeCompletions:
    def __init__(self) -> None:
        self.last_messages: list[dict[str, str]] = []

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.last_messages = list(kwargs.get("messages", []))
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            '{"tasks":[{"id":1,"description":"Create endpoint",'
                            '"depends_on":[]}],"subgoals":["Create endpoint"]}'
                        )
                    )
                )
            ]
        )


class _FakeClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions())


def test_planner_formats_prompt_with_project_root_for_model_path() -> None:
    plan_file = "tmp_plan_planner_prompt_root.md"
    path = Path(plan_file)
    try:
        config = AgentConfig(
            api_key="stub-key",
            plan_file=plan_file,
            planning_max_steps=3,
        )
        planner = PlannerAgent(config)
        fake_client = _FakeClient()
        planner._build_client = lambda: fake_client  # type: ignore[method-assign]

        result = planner.build_plan(
            user_request="Build a FastAPI endpoint for X and add tests",
            project_root="D:\\test\\fastapi-app\\",
        )

        assert len(result["plan_tasks"]) == 1
        assert not result["create_plan_result"].startswith("Error:")
        prompt = fake_client.chat.completions.last_messages[1]["content"]
        assert "D:/test/fastapi-app" in prompt
    finally:
        if path.exists():
            try:
                path.unlink()
            except PermissionError:
                pass
