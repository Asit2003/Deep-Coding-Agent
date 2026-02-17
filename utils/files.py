"""Comprehensive filesystem tools for project automation."""

import difflib
import fnmatch
import hashlib
import os
import shutil
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from zipfile import ZIP_DEFLATED, ZipFile



WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
IGNORE_DIRS = {".git", "node_modules", "__pycache__"}
MAX_FILE_SIZE = 100_000  # 100 KB
DEFAULT_MAX_SEARCH_RESULTS = 200


def _resolve_workspace_path(path_value: str) -> Path:
    """Resolve a path and block traversal outside workspace root."""
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
    """Format a path relative to workspace root for stable output."""
    return path.relative_to(WORKSPACE_ROOT).as_posix()


def _iter_files(
    root: Path,
    *,
    include_hidden: bool = False,
    ignore_dirs: Optional[set[str]] = None,
) -> Iterator[Path]:
    """Iterate files under root while applying directory and hidden filters."""
    ignored = ignore_dirs or set()
    for current_root, dirs, files in os.walk(root):
        dirs[:] = [
            entry
            for entry in dirs
            if entry not in ignored and (include_hidden or not entry.startswith("."))
        ]
        for file_name in files:
            if not include_hidden and file_name.startswith("."):
                continue
            yield Path(current_root) / file_name


def _is_probably_binary(file_path: Path) -> bool:
    """Detect binary files using a null-byte check on an initial chunk."""
    try:
        with file_path.open("rb") as file:
            chunk = file.read(1024)
    except OSError:
        return True
    return b"\x00" in chunk


def _read_text_file(file_path: Path) -> str:
    """Read a text file with UTF-8 encoding."""
    return file_path.read_text(encoding="utf-8")


def _safe_list_files_impl(
    directory: str,
    max_file_size: int,
    include_hidden: bool,
) -> list[str]:
    """Core implementation for filtered recursive file listing."""
    if max_file_size < 0:
        return ["Error: max_file_size must be >= 0"]

    try:
        target_dir = _resolve_workspace_path(directory)
    except ValueError as err:
        return [f"Error: {err}"]

    if not target_dir.exists():
        return [f"Error: Directory '{directory}' not found"]
    if not target_dir.is_dir():
        return [f"Error: '{directory}' is not a directory"]

    collected: list[str] = []
    for file_path in _iter_files(
        target_dir,
        include_hidden=include_hidden,
        ignore_dirs=IGNORE_DIRS,
    ):
        try:
            if file_path.stat().st_size > max_file_size:
                continue
        except OSError:
            continue
        if _is_probably_binary(file_path):
            continue
        collected.append(_to_workspace_relative(file_path))

    collected.sort()
    return collected


def _format_numbered_lines(lines: list[str], start: int, end: Optional[int]) -> str:
    """Render a line slice with 1-based line numbers."""
    stop = len(lines) if end is None else min(end, len(lines))
    result = []
    for idx in range(start - 1, stop):
        result.append(f"{idx + 1:6d}\t{lines[idx]}")
    return "\n".join(result)


def _read_file_lines_impl(file_path: str, start: int, end: Optional[int]) -> str:
    """Core implementation for range-based line reads."""
    if start < 1:
        return "Error: start must be >= 1"
    if end is not None and end < start:
        return "Error: end must be >= start"

    try:
        resolved = _resolve_workspace_path(file_path)
    except ValueError as err:
        return f"Error: {err}"

    if not resolved.exists() or not resolved.is_file():
        return f"Error: File '{file_path}' not found"

    try:
        lines = _read_text_file(resolved).splitlines()
    except UnicodeDecodeError:
        return f"Error: '{file_path}' is not UTF-8 text"
    except OSError as err:
        return f"Error: Unable to read '{file_path}': {err}"

    if not lines:
        return "System reminder: File exists but has empty contents"
    if start > len(lines):
        return f"Error: start line {start} exceeds file length ({len(lines)} lines)"

    return _format_numbered_lines(lines, start, end)


def get_current_directory() -> str:
    """Return the current working directory."""
    return os.getcwd()


def safe_resolve_path(path: str) -> str:
    """Safely resolve a path and return workspace-relative output."""
    try:
        resolved = _resolve_workspace_path(path)
        return _to_workspace_relative(resolved)
    except ValueError as err:
        return f"Error: {err}"


def list_files(directory: str = ".") -> list[str]:
    """Return one-level directory entries."""
    try:
        target_dir = _resolve_workspace_path(directory)
    except ValueError as err:
        return [f"Error: {err}"]

    if not target_dir.exists():
        return [f"Error: Directory '{directory}' not found"]
    if not target_dir.is_dir():
        return [f"Error: '{directory}' is not a directory"]

    try:
        entries = []
        for item in sorted(target_dir.iterdir(), key=lambda p: p.name.lower()):
            rel = _to_workspace_relative(item)
            entries.append(f"{rel}/" if item.is_dir() else rel)
        return entries
    except OSError as err:
        return [f"Error: Unable to list '{directory}': {err}"]


def list_all_files(directory: str = ".") -> list[str]:
    """Return recursive file paths."""
    try:
        target_dir = _resolve_workspace_path(directory)
    except ValueError as err:
        return [f"Error: {err}"]

    if not target_dir.exists():
        return [f"Error: Directory '{directory}' not found"]
    if not target_dir.is_dir():
        return [f"Error: '{directory}' is not a directory"]

    files = [
        _to_workspace_relative(path) for path in target_dir.rglob("*") if path.is_file()
    ]
    files.sort()
    return files


def safe_list_files(
    directory: str = ".",
    max_file_size: int = MAX_FILE_SIZE,
    include_hidden: bool = False,
) -> list[str]:
    """Return a filtered recursive file list for safe project scanning."""
    return _safe_list_files_impl(
        directory=directory,
        max_file_size=max_file_size,
        include_hidden=include_hidden,
    )


def read_file(file_path: str) -> str:
    """Read complete file content."""
    try:
        resolved = _resolve_workspace_path(file_path)
    except ValueError as err:
        return f"Error: {err}"

    if not resolved.exists():
        return f"Error: File '{file_path}' not found"
    if not resolved.is_file():
        return f"Error: '{file_path}' is not a file"

    try:
        return _read_text_file(resolved)
    except UnicodeDecodeError:
        return f"Error: '{file_path}' is not UTF-8 text"
    except OSError as err:
        return f"Error: Unable to read '{file_path}': {err}"


def read_file_lines(file_path: str, start: int = 1, end: Optional[int] = None) -> str:
    """Read selected lines from a file."""
    return _read_file_lines_impl(file_path=file_path, start=start, end=end)


def head_file(file_path: str, n: int = 50) -> str:
    """Return file head."""
    if n <= 0:
        return "Error: n must be > 0"
    return _read_file_lines_impl(file_path=file_path, start=1, end=n)


def tail_file(file_path: str, n: int = 50) -> str:
    """Return file tail."""
    if n <= 0:
        return "Error: n must be > 0"

    try:
        resolved = _resolve_workspace_path(file_path)
    except ValueError as err:
        return f"Error: {err}"

    if not resolved.exists() or not resolved.is_file():
        return f"Error: File '{file_path}' not found"

    try:
        lines = _read_text_file(resolved).splitlines()
    except UnicodeDecodeError:
        return f"Error: '{file_path}' is not UTF-8 text"
    except OSError as err:
        return f"Error: Unable to read '{file_path}': {err}"

    if not lines:
        return "System reminder: File exists but has empty contents"

    start_line = max(1, len(lines) - n + 1)
    return _format_numbered_lines(lines, start_line, len(lines))


def get_file_tree(directory: str = ".", indent_unit: str = "    ") -> str:
    """Return a recursive file tree."""
    try:
        target_dir = _resolve_workspace_path(directory)
    except ValueError as err:
        return f"Error: {err}"

    if not target_dir.exists():
        return f"Error: Directory '{directory}' not found"
    if not target_dir.is_dir():
        return f"Error: '{directory}' is not a directory"

    lines: list[str] = []

    def walk(current: Path, level: int) -> None:
        for item in sorted(
            current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
        ):
            marker = "/" if item.is_dir() else ""
            lines.append(f"{indent_unit * level}{item.name}{marker}")
            if item.is_dir():
                walk(item, level + 1)

    walk(target_dir, 0)
    return "\n".join(lines)


def build_project_context(directory: str = ".") -> str:
    """Build a simple context payload for LLM prompts."""
    files = _safe_list_files_impl(
        directory=directory, max_file_size=MAX_FILE_SIZE, include_hidden=False
    )
    if isinstance(files, list) and files and files[0].startswith("Error:"):
        return files[0]

    context = "Project File List:\n"
    for file_path in files:
        context += f"- {file_path}\n"
    return context


def write_file(
    file_path: str,
    content: str,
    overwrite: bool = True,
    create_dirs: bool = True,
) -> str:
    """Write file content."""
    try:
        resolved = _resolve_workspace_path(file_path)
    except ValueError as err:
        return f"Error: {err}"

    if resolved.exists() and resolved.is_dir():
        return f"Error: '{file_path}' is a directory"
    if resolved.exists() and not overwrite:
        return f"Error: '{file_path}' already exists and overwrite is False"

    try:
        if create_dirs:
            resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return f"Updated file {_to_workspace_relative(resolved)}"
    except OSError as err:
        return f"Error: Unable to write '{file_path}': {err}"


def append_file(file_path: str, content: str, create_dirs: bool = True) -> str:
    """Append content to a file."""
    try:
        resolved = _resolve_workspace_path(file_path)
    except ValueError as err:
        return f"Error: {err}"

    if resolved.exists() and resolved.is_dir():
        return f"Error: '{file_path}' is a directory"

    try:
        if create_dirs:
            resolved.parent.mkdir(parents=True, exist_ok=True)
        with resolved.open("a", encoding="utf-8") as file:
            file.write(content)
        return f"Appended content to {_to_workspace_relative(resolved)}"
    except OSError as err:
        return f"Error: Unable to append '{file_path}': {err}"


def create_file(
    file_path: str, create_dirs: bool = True, overwrite: bool = False
) -> str:
    """Create a new empty file."""
    try:
        resolved = _resolve_workspace_path(file_path)
    except ValueError as err:
        return f"Error: {err}"

    if resolved.exists() and resolved.is_dir():
        return f"Error: '{file_path}' is a directory"
    if resolved.exists() and not overwrite:
        return f"Error: '{file_path}' already exists and overwrite is False"

    try:
        if create_dirs:
            resolved.parent.mkdir(parents=True, exist_ok=True)
        if overwrite:
            resolved.write_text("", encoding="utf-8")
        else:
            resolved.touch(exist_ok=False)
        return f"Created file {_to_workspace_relative(resolved)}"
    except OSError as err:
        return f"Error: Unable to create '{file_path}': {err}"


def delete_file(file_path: str, missing_ok: bool = False) -> str:
    """Delete a file."""
    try:
        resolved = _resolve_workspace_path(file_path)
    except ValueError as err:
        return f"Error: {err}"

    if not resolved.exists():
        if missing_ok:
            return f"File '{file_path}' does not exist (ignored)"
        return f"Error: File '{file_path}' not found"
    if not resolved.is_file():
        return f"Error: '{file_path}' is not a file"

    try:
        resolved.unlink()
        return f"Deleted file {_to_workspace_relative(resolved)}"
    except OSError as err:
        return f"Error: Unable to delete '{file_path}': {err}"


def make_directory(path: str, parents: bool = True, exist_ok: bool = True) -> str:
    """Create a directory."""
    try:
        resolved = _resolve_workspace_path(path)
    except ValueError as err:
        return f"Error: {err}"

    try:
        resolved.mkdir(parents=parents, exist_ok=exist_ok)
        return f"Created directory {_to_workspace_relative(resolved)}/"
    except OSError as err:
        return f"Error: Unable to create directory '{path}': {err}"


def delete_directory(
    path: str, recursive: bool = False, missing_ok: bool = False
) -> str:
    """Delete a directory."""
    try:
        resolved = _resolve_workspace_path(path)
    except ValueError as err:
        return f"Error: {err}"

    if not resolved.exists():
        if missing_ok:
            return f"Directory '{path}' does not exist (ignored)"
        return f"Error: Directory '{path}' not found"
    if not resolved.is_dir():
        return f"Error: '{path}' is not a directory"

    try:
        if recursive:
            shutil.rmtree(resolved)
        else:
            resolved.rmdir()
        return f"Deleted directory {_to_workspace_relative(resolved)}/"
    except OSError as err:
        return f"Error: Unable to delete directory '{path}': {err}"


def copy_file(
    source: str,
    destination: str,
    overwrite: bool = False,
    create_dirs: bool = True,
) -> str:
    """Copy a file."""
    try:
        src = _resolve_workspace_path(source)
        dst = _resolve_workspace_path(destination)
    except ValueError as err:
        return f"Error: {err}"

    if not src.exists() or not src.is_file():
        return f"Error: Source file '{source}' not found"
    if dst.exists() and dst.is_dir():
        dst = dst / src.name
    if dst.exists() and not overwrite:
        return (
            f"Error: Destination '{_to_workspace_relative(dst)}' exists "
            "and overwrite is False"
        )

    try:
        if create_dirs:
            dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return f"Copied {_to_workspace_relative(src)} -> {_to_workspace_relative(dst)}"
    except OSError as err:
        return f"Error: Unable to copy file: {err}"


def move_path(
    source: str,
    destination: str,
    overwrite: bool = False,
    create_dirs: bool = True,
) -> str:
    """Move a file or directory."""
    try:
        src = _resolve_workspace_path(source)
        dst = _resolve_workspace_path(destination)
    except ValueError as err:
        return f"Error: {err}"

    if not src.exists():
        return f"Error: Source path '{source}' not found"
    if dst.exists() and dst.is_dir():
        dst = dst / src.name

    if dst.exists():
        if not overwrite:
            return (
                f"Error: Destination '{_to_workspace_relative(dst)}' exists "
                "and overwrite is False"
            )
        try:
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        except OSError as err:
            return (
                "Error: Unable to clear destination "
                f"'{_to_workspace_relative(dst)}': {err}"
            )

    try:
        if create_dirs:
            dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return f"Moved {_to_workspace_relative(src)} -> {_to_workspace_relative(dst)}"
    except OSError as err:
        return f"Error: Unable to move path: {err}"


def rename_path(source: str, new_name: str, overwrite: bool = False) -> str:
    """Rename a path in place."""
    if not new_name or Path(new_name).name != new_name:
        return "Error: new_name must be a single file or directory name"

    try:
        src = _resolve_workspace_path(source)
    except ValueError as err:
        return f"Error: {err}"

    if not src.exists():
        return f"Error: Source path '{source}' not found"

    dst = src.with_name(new_name)
    if dst.exists():
        if not overwrite:
            return (
                f"Error: Target '{_to_workspace_relative(dst)}' exists "
                "and overwrite is False"
            )
        try:
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        except OSError as err:
            return (
                "Error: Unable to clear existing target "
                f"'{_to_workspace_relative(dst)}': {err}"
            )

    try:
        src.rename(dst)
        return f"Renamed {_to_workspace_relative(src)} -> {_to_workspace_relative(dst)}"
    except OSError as err:
        return f"Error: Unable to rename path: {err}"


def path_exists(path: str) -> bool:
    """Return True if path exists and resolves inside workspace."""
    try:
        return _resolve_workspace_path(path).exists()
    except ValueError:
        return False


def is_file(path: str) -> bool:
    """Return True if path is a file."""
    try:
        return _resolve_workspace_path(path).is_file()
    except ValueError:
        return False


def is_dir(path: str) -> bool:
    """Return True if path is a directory."""
    try:
        return _resolve_workspace_path(path).is_dir()
    except ValueError:
        return False


def get_file_info(path: str) -> dict[str, Any]:
    """Return filesystem metadata."""
    try:
        resolved = _resolve_workspace_path(path)
    except ValueError as err:
        return {"error": str(err)}

    if not resolved.exists():
        return {"path": path, "exists": False}

    try:
        stats = resolved.stat()
    except OSError as err:
        return {"error": f"Unable to stat '{path}': {err}"}

    return {
        "path": _to_workspace_relative(resolved),
        "absolute_path": resolved.as_posix(),
        "exists": True,
        "is_file": resolved.is_file(),
        "is_dir": resolved.is_dir(),
        "size_bytes": stats.st_size,
        "modified_utc": datetime.fromtimestamp(
            stats.st_mtime, tz=timezone.utc
        ).isoformat(),
        "created_utc": datetime.fromtimestamp(
            stats.st_ctime, tz=timezone.utc
        ).isoformat(),
        "permissions_octal": oct(stats.st_mode & 0o777),
        "readable": os.access(resolved, os.R_OK),
        "writable": os.access(resolved, os.W_OK),
        "executable": os.access(resolved, os.X_OK),
    }


def find_files(pattern: str, root: str = ".") -> list[str]:
    """Find files by pattern."""
    if not pattern:
        return ["Error: pattern must not be empty"]

    try:
        root_dir = _resolve_workspace_path(root)
    except ValueError as err:
        return [f"Error: {err}"]

    if not root_dir.exists() or not root_dir.is_dir():
        return [f"Error: Root directory '{root}' not found"]

    matches: list[str] = []
    for path in root_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = _to_workspace_relative(path)
        if fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(rel, pattern):
            matches.append(rel)
    matches.sort()
    return matches


def search_in_files(
    query: str,
    root: str = ".",
    case_sensitive: bool = False,
    max_results: int = DEFAULT_MAX_SEARCH_RESULTS,
) -> list[dict[str, Any]]:
    """Search for a string in text files."""
    if not query:
        return [{"error": "query must not be empty"}]
    if max_results <= 0:
        return [{"error": "max_results must be > 0"}]

    try:
        root_dir = _resolve_workspace_path(root)
    except ValueError as err:
        return [{"error": str(err)}]

    if not root_dir.exists() or not root_dir.is_dir():
        return [{"error": f"Root directory '{root}' not found"}]

    results: list[dict[str, Any]] = []
    needle = query if case_sensitive else query.lower()

    for file_path in _iter_files(
        root_dir, include_hidden=False, ignore_dirs=IGNORE_DIRS
    ):
        try:
            if file_path.stat().st_size > MAX_FILE_SIZE:
                continue
        except OSError:
            continue
        if _is_probably_binary(file_path):
            continue

        try:
            lines = _read_text_file(file_path).splitlines()
        except (UnicodeDecodeError, OSError):
            continue

        for line_number, line in enumerate(lines, start=1):
            haystack = line if case_sensitive else line.lower()
            if needle in haystack:
                results.append(
                    {
                        "path": _to_workspace_relative(file_path),
                        "line_number": line_number,
                        "line": line[:1000],
                    }
                )
                if len(results) >= max_results:
                    return results

    return results


def replace_in_file(file_path: str, old: str, new: str, count: int = -1) -> str:
    """Replace string content in a text file."""
    if old == "":
        return "Error: old must not be empty"
    if count == 0:
        return "No changes made (count=0)"

    try:
        resolved = _resolve_workspace_path(file_path)
    except ValueError as err:
        return f"Error: {err}"

    if not resolved.exists() or not resolved.is_file():
        return f"Error: File '{file_path}' not found"

    try:
        content = _read_text_file(resolved)
    except UnicodeDecodeError:
        return f"Error: '{file_path}' is not UTF-8 text"
    except OSError as err:
        return f"Error: Unable to read '{file_path}': {err}"

    if count < 0:
        replacements = content.count(old)
        updated = content.replace(old, new)
    else:
        replacements = min(content.count(old), count)
        updated = content.replace(old, new, count)

    if replacements == 0:
        return f"No matches found in {_to_workspace_relative(resolved)}"

    try:
        resolved.write_text(updated, encoding="utf-8")
    except OSError as err:
        return f"Error: Unable to write '{file_path}': {err}"

    return (
        f"Replaced {replacements} occurrence(s) in {_to_workspace_relative(resolved)}"
    )


def compute_file_hash(file_path: str, algorithm: str = "sha256") -> str:
    """Compute file digest."""
    try:
        resolved = _resolve_workspace_path(file_path)
    except ValueError as err:
        return f"Error: {err}"

    if not resolved.exists() or not resolved.is_file():
        return f"Error: File '{file_path}' not found"

    try:
        hasher = hashlib.new(algorithm)
    except ValueError:
        return f"Error: Unsupported hash algorithm '{algorithm}'"

    try:
        with resolved.open("rb") as file:
            for chunk in iter(lambda: file.read(8192), b""):
                hasher.update(chunk)
    except OSError as err:
        return f"Error: Unable to hash '{file_path}': {err}"

    return f"{algorithm}:{hasher.hexdigest()}"


def diff_files(file_a: str, file_b: str, context_lines: int = 3) -> str:
    """Return textual diff output."""
    if context_lines < 0:
        return "Error: context_lines must be >= 0"

    try:
        path_a = _resolve_workspace_path(file_a)
        path_b = _resolve_workspace_path(file_b)
    except ValueError as err:
        return f"Error: {err}"

    if not path_a.exists() or not path_a.is_file():
        return f"Error: File '{file_a}' not found"
    if not path_b.exists() or not path_b.is_file():
        return f"Error: File '{file_b}' not found"

    try:
        lines_a = _read_text_file(path_a).splitlines(keepends=True)
        lines_b = _read_text_file(path_b).splitlines(keepends=True)
    except UnicodeDecodeError:
        return "Error: Both files must be UTF-8 text for diff"
    except OSError as err:
        return f"Error: Unable to read files for diff: {err}"

    diff = difflib.unified_diff(
        lines_a,
        lines_b,
        fromfile=_to_workspace_relative(path_a),
        tofile=_to_workspace_relative(path_b),
        n=context_lines,
    )
    output = "".join(diff)
    return output if output else "No differences found."


def zip_paths(paths: list[str], output_zip: str, overwrite: bool = False) -> str:
    """Zip multiple paths into one archive."""
    if not paths:
        return "Error: paths must not be empty"

    try:
        zip_path = _resolve_workspace_path(output_zip)
    except ValueError as err:
        return f"Error: {err}"

    if zip_path.exists() and not overwrite:
        return f"Error: '{output_zip}' already exists and overwrite is False"

    try:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        return f"Error: Unable to prepare output path '{output_zip}': {err}"

    added = 0
    try:
        with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED) as archive:
            for raw_path in paths:
                src = _resolve_workspace_path(raw_path)
                if not src.exists():
                    return f"Error: Input path '{raw_path}' not found"

                if src.is_file():
                    if src == zip_path:
                        continue
                    archive.write(src, arcname=_to_workspace_relative(src))
                    added += 1
                else:
                    for item in src.rglob("*"):
                        if not item.is_file():
                            continue
                        if item == zip_path:
                            continue
                        archive.write(item, arcname=_to_workspace_relative(item))
                        added += 1
    except ValueError as err:
        return f"Error: {err}"
    except OSError as err:
        return f"Error: Unable to create zip '{output_zip}': {err}"

    return f"Created zip {_to_workspace_relative(zip_path)} with {added} file(s)"


def unzip_file(zip_path: str, destination: str = ".", overwrite: bool = False) -> str:
    """Extract zip archive contents."""
    try:
        archive_path = _resolve_workspace_path(zip_path)
        dest_dir = _resolve_workspace_path(destination)
    except ValueError as err:
        return f"Error: {err}"

    if not archive_path.exists() or not archive_path.is_file():
        return f"Error: Zip file '{zip_path}' not found"

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        return f"Error: Unable to create destination '{destination}': {err}"

    extracted = 0
    try:
        with ZipFile(archive_path, mode="r") as archive:
            for member in archive.infolist():
                target = (dest_dir / member.filename).resolve()
                try:
                    target.relative_to(dest_dir)
                except ValueError:
                    return f"Error: Unsafe zip entry '{member.filename}'"

                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue

                if target.exists() and not overwrite:
                    return (
                        "Error: Destination file exists and overwrite is False: "
                        f"{_to_workspace_relative(target)}"
                    )

                target.parent.mkdir(parents=True, exist_ok=True)
                with (
                    archive.open(member, "r") as src_file,
                    target.open("wb") as dst_file,
                ):
                    shutil.copyfileobj(src_file, dst_file)
                extracted += 1
    except OSError as err:
        return f"Error: Unable to extract zip '{zip_path}': {err}"

    return (
        f"Extracted {extracted} file(s) from {_to_workspace_relative(archive_path)} "
        f"to {_to_workspace_relative(dest_dir)}/"
    )
