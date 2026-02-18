import json
from pathlib import Path

from utils import plans


def _read_state(plan_file: str) -> dict:
    content = Path(plan_file).read_text(encoding="utf-8")
    match = plans.STATE_PATTERN.search(content)
    assert match is not None
    return json.loads(match.group(1))


def _plan_file(name: str) -> str:
    return f"tmp_plan_{name}.md"


def test_create_plan_and_update_step() -> None:
    plan_file = _plan_file("test_create_update")
    plan_path = Path(plan_file)
    try:
        created = plans.create_plan(
            task="Implement planning tools",
            steps=["Inspect code", "Implement changes", "Run checks"],
            plan_file=plan_file,
            overwrite=True,
        )
        assert created.startswith("Created plan")
        assert plan_path.exists()

        initial_state = _read_state(plan_file)
        assert initial_state["steps"][0]["status"] == "in_progress"
        assert initial_state["status"] == "active"

        updated = plans.update_plan(
            step_number=1,
            status="completed",
            note="Finished repository scan",
            plan_file=plan_file,
        )
        assert updated.startswith("Updated step 1")

        state = _read_state(plan_file)
        assert state["steps"][0]["status"] == "completed"
        assert any(
            entry["message"] == "Finished repository scan"
            for entry in state["progress_log"]
        )
    finally:
        if plan_path.exists():
            try:
                plan_path.unlink()
            except PermissionError:
                pass


def test_set_subgoals_replace_and_append() -> None:
    plan_file = _plan_file("test_subgoals")
    plan_path = Path(plan_file)
    try:
        plans.create_plan(
            task="Test subgoals",
            steps=["Step A"],
            plan_file=plan_file,
            overwrite=True,
        )

        replaced = plans.set_subgoals(
            subgoals=["Code quality", "Add tests"],
            plan_file=plan_file,
            replace=True,
        )
        assert replaced.startswith("Set 2 subgoal")

        appended = plans.set_subgoals(
            subgoals=["Document usage"],
            plan_file=plan_file,
            replace=False,
        )
        assert appended.startswith("Updated 3 subgoal")

        state = _read_state(plan_file)
        descriptions = [item["description"] for item in state["subgoals"]]
        assert descriptions == ["Code quality", "Add tests", "Document usage"]
    finally:
        if plan_path.exists():
            try:
                plan_path.unlink()
            except PermissionError:
                pass


def test_track_progress_complete_and_cleanup() -> None:
    plan_file = _plan_file("test_progress_cleanup")
    plan_path = Path(plan_file)
    try:
        plans.create_plan(
            task="Finalize workflow",
            steps=["Only step"],
            plan_file=plan_file,
            overwrite=True,
        )

        progress = plans.track_progress(
            message="Half complete",
            percent_complete=50,
            plan_file=plan_file,
        )
        assert progress.startswith("Logged progress")

        state = _read_state(plan_file)
        assert state["percent_complete"] == 50
        assert state["status"] == "active"

        cleanup = plans.track_progress(
            message="Done",
            complete_plan=True,
            cleanup_plan_file=True,
            plan_file=plan_file,
        )
        assert cleanup.startswith("Completed plan and removed") or cleanup.startswith(
            "Warning: Plan completed but cleanup failed"
        )
        if plan_path.exists():
            state_after_cleanup = _read_state(plan_file)
            assert state_after_cleanup["status"] == "completed"
        else:
            assert not plan_path.exists()
    finally:
        if plan_path.exists():
            try:
                plan_path.unlink()
            except PermissionError:
                pass


def test_reflect_on_plan_finalize_and_cleanup() -> None:
    plan_file = _plan_file("test_reflection_cleanup")
    plan_path = Path(plan_file)
    try:
        plans.create_plan(
            task="Reflection path",
            steps=["Plan", "Build"],
            plan_file=plan_file,
            overwrite=True,
        )

        reflection = plans.reflect_on_plan(
            summary="Execution looks stable",
            risks=["Low test coverage"],
            next_actions=["Add integration test"],
            plan_file=plan_file,
        )
        assert reflection.startswith("Recorded reflection")

        state = _read_state(plan_file)
        assert len(state["reflections"]) == 1

        finalized = plans.reflect_on_plan(
            summary="All work completed",
            finalize=True,
            cleanup_plan_file=True,
            plan_file=plan_file,
        )
        assert (
            finalized.startswith("Completed plan and removed")
            or finalized.startswith("Warning: Plan completed but cleanup failed")
        )
        if plan_path.exists():
            finalized_state = _read_state(plan_file)
            assert finalized_state["status"] == "completed"
        else:
            assert not plan_path.exists()
    finally:
        if plan_path.exists():
            try:
                plan_path.unlink()
            except PermissionError:
                pass


def test_decompose_task_returns_steps() -> None:
    steps = plans.decompose_task(
        "Inspect code then implement plan tools then run tests",
        max_steps=4,
    )
    assert not any(step.startswith("Error:") for step in steps)
    assert 2 <= len(steps) <= 4
