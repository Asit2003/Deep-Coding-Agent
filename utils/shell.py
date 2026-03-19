"""Safe shell execution utilities for agent workflows."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_OUTPUT_CHARS = 12_000
ALLOWED_COMMANDS = {"git", "py", "pytest", "python", "ruff", "uv"}
READ_ONLY_GIT_SUBCOMMANDS = {
    "branch",
    "diff",
    "log",
    "ls-files",
    "rev-parse",
    "show",
    "status",
}


def _resolve_workspace_path(path_value: str) -> Path:
    """Resolve a path and reject traversal outside the workspace root."""
    raw_path = Path(path_value).expanduser()
    resolved = (
        raw_path.resolve()
        if raw_path.is_absolute()
        else (WORKSPACE_ROOT / raw_path).resolve()
    )
    try:
        resolved.relative_to(WORKSPACE_ROOT)
    except ValueError as err:
        raise ValueError(
            f"Path '{path_value}' is outside workspace root '{WORKSPACE_ROOT.as_posix()}'"
        ) from err
    return resolved


def _to_workspace_relative(path: Path) -> str:
    """Render a path relative to the workspace root."""
    return path.relative_to(WORKSPACE_ROOT).as_posix()


def _command_name(args: list[str]) -> str:
    """Normalize the executable name for allowlist checks."""
    return Path(args[0]).stem.lower()


def _resolve_scoped_cwd(cwd: str, base_directory: str) -> Path:
    """Resolve cwd within a workspace-relative base directory."""
    base_path = _resolve_workspace_path(base_directory or ".")
    raw_cwd = str(cwd or ".").strip().replace("\\", "/")
    if raw_cwd in {"", ".", "./"}:
        return base_path

    base_prefix = _to_workspace_relative(base_path)
    if raw_cwd == base_prefix or raw_cwd.startswith(f"{base_prefix}/"):
        resolved = _resolve_workspace_path(raw_cwd)
    else:
        resolved = (base_path / raw_cwd).resolve()
        try:
            resolved.relative_to(WORKSPACE_ROOT)
        except ValueError as err:
            raise ValueError(
                f"Working directory '{cwd}' is outside workspace root "
                f"'{WORKSPACE_ROOT.as_posix()}'"
            ) from err

    try:
        resolved.relative_to(base_path)
    except ValueError as err:
        raise ValueError(
            f"Working directory '{cwd}' must stay inside '{base_prefix or '.'}'"
        ) from err

    return resolved


def _validate_command(args: list[str]) -> str | None:
    """Validate command allowlist and reject destructive or interactive patterns."""
    if not isinstance(args, list) or not args:
        return "args must contain at least one command token"

    normalized_args = [str(item).strip() for item in args]
    if any(not item for item in normalized_args):
        return "args must not contain empty command tokens"

    command = _command_name(normalized_args)
    if command not in ALLOWED_COMMANDS:
        return f"Command '{normalized_args[0]}' is not allowlisted"

    if command in {"python", "py"}:
        if len(normalized_args) == 1:
            return "Interactive Python sessions are not allowed"
        if normalized_args[1] in {"-i", "-m", "-q"} and len(normalized_args) == 2:
            return "Interactive Python sessions are not allowed"

    if command == "uv":
        if len(normalized_args) < 3 or normalized_args[1] != "run":
            return "Only 'uv run ...' commands are allowed"

    if command == "git":
        if len(normalized_args) < 2:
            return "Git subcommand is required"
        subcommand = normalized_args[1].lower()
        if subcommand not in READ_ONLY_GIT_SUBCOMMANDS:
            return f"Git subcommand '{subcommand}' is not allowed"

    return None


def _truncate_output(text: str, max_chars: int) -> str:
    """Truncate large command output to keep tool responses bounded."""
    if max_chars < 200:
        max_chars = 200
    if len(text) <= max_chars:
        return text

    head_chars = max_chars // 2
    tail_chars = max_chars - head_chars
    omitted = len(text) - max_chars
    return (
        f"{text[:head_chars]}\n"
        f"...[truncated {omitted} characters]...\n"
        f"{text[-tail_chars:]}"
    )


def run_shell_command(
    args: list[str],
    cwd: str = ".",
    *,
    base_directory: str = ".",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS,
) -> dict[str, Any]:
    """Run an allowlisted non-interactive command inside a scoped directory."""
    if timeout_seconds <= 0:
        return {
            "ok": False,
            "command": args,
            "cwd": cwd,
            "exit_code": None,
            "stdout": "",
            "stderr": "timeout_seconds must be > 0",
            "timed_out": False,
        }

    validation_error = _validate_command(args)
    if validation_error:
        return {
            "ok": False,
            "command": args,
            "cwd": cwd,
            "exit_code": None,
            "stdout": "",
            "stderr": validation_error,
            "timed_out": False,
        }

    try:
        resolved_cwd = _resolve_scoped_cwd(cwd=cwd, base_directory=base_directory)
    except ValueError as err:
        return {
            "ok": False,
            "command": args,
            "cwd": cwd,
            "exit_code": None,
            "stdout": "",
            "stderr": str(err),
            "timed_out": False,
        }

    if not resolved_cwd.exists() or not resolved_cwd.is_dir():
        return {
            "ok": False,
            "command": args,
            "cwd": _to_workspace_relative(resolved_cwd),
            "exit_code": None,
            "stdout": "",
            "stderr": f"Working directory '{_to_workspace_relative(resolved_cwd)}' not found",
            "timed_out": False,
        }

    try:
        completed = subprocess.run(
            [str(item) for item in args],
            cwd=resolved_cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
        )
    except subprocess.TimeoutExpired as err:
        stdout = _truncate_output((err.stdout or "").strip(), max_output_chars)
        stderr = _truncate_output((err.stderr or "").strip(), max_output_chars)
        message = (
            stderr or stdout or f"Command timed out after {timeout_seconds} second(s)"
        )
        return {
            "ok": False,
            "command": args,
            "cwd": _to_workspace_relative(resolved_cwd),
            "exit_code": None,
            "stdout": stdout,
            "stderr": message,
            "timed_out": True,
        }
    except OSError as err:
        return {
            "ok": False,
            "command": args,
            "cwd": _to_workspace_relative(resolved_cwd),
            "exit_code": None,
            "stdout": "",
            "stderr": str(err),
            "timed_out": False,
        }

    stdout = _truncate_output(completed.stdout.strip(), max_output_chars)
    stderr = _truncate_output(completed.stderr.strip(), max_output_chars)
    return {
        "ok": completed.returncode == 0,
        "command": args,
        "cwd": _to_workspace_relative(resolved_cwd),
        "exit_code": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": False,
    }


__all__ = [
    "DEFAULT_MAX_OUTPUT_CHARS",
    "DEFAULT_TIMEOUT_SECONDS",
    "run_shell_command",
]
