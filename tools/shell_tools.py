"""Tool bindings for guarded shell execution."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from utils import shell as shell_ops


def make_run_shell_tool(base_directory: str = ".") -> Any:
    """Build a scoped shell tool bound to a project or workspace directory."""

    @tool(parse_docstring=False)
    def run_shell(
        command: list[str],
        cwd: str = ".",
        timeout_seconds: int = shell_ops.DEFAULT_TIMEOUT_SECONDS,
    ) -> dict[str, Any]:
        """Run an allowlisted non-interactive command within a scoped directory.

        Args:
            command: Command tokens, for example ["uv", "run", "pytest", "-q"].
            cwd: Optional working directory relative to the scoped base directory.
            timeout_seconds: Optional timeout in seconds.
        """

        return shell_ops.run_shell_command(
            args=command,
            cwd=cwd,
            base_directory=base_directory,
            timeout_seconds=timeout_seconds,
        )

    return run_shell


__all__ = ["make_run_shell_tool"]
