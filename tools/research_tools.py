"""Research tool bindings for local project and docs discovery."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from utils import files as file_ops


@tool(parse_docstring=False)
def list_reference_docs(directory: str = "Docs") -> list[str]:
    """List documentation/reference files under a directory.

    Args:
        directory: Root directory to scan for docs.
    """
    return file_ops.safe_list_files(
        directory=directory,
        max_file_size=250_000,
        include_hidden=False,
    )


@tool(parse_docstring=False)
def search_reference_notes(
    query: str,
    root: str = "Docs",
    max_results: int = 50,
) -> list[dict[str, Any]]:
    """Search documentation text for a query string.

    Args:
        query: Search text.
        root: Directory root to scan.
        max_results: Maximum returned matches.
    """
    return file_ops.search_in_files(
        query=query,
        root=root,
        case_sensitive=False,
        max_results=max_results,
    )


@tool(parse_docstring=False)
def search_project_context(
    query: str,
    root: str = ".",
    max_results: int = 75,
) -> list[dict[str, Any]]:
    """Search repository files for implementation clues.

    Args:
        query: Search text.
        root: Root directory for search.
        max_results: Maximum number of match records.
    """
    return file_ops.search_in_files(
        query=query,
        root=root,
        case_sensitive=False,
        max_results=max_results,
    )


__all__ = [
    "list_reference_docs",
    "search_reference_notes",
    "search_project_context",
]
