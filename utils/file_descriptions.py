"""Detailed descriptions for filesystem tools used by the coding agent."""

FILE_USAGE_INSTRUCTIONS = """You have access to a real filesystem scoped to this project workspace.

Recommended workflow:
1. Orient first: use list_files() or get_file_tree() to understand current structure.
2. Read before editing: inspect content with read_file() or read_file_lines().
3. Edit safely: use write_file(), append_file(), replace_in_file(), copy_file(), or move_path().
4. Validate results: use diff_files(), compute_file_hash(), get_file_info(), or read_file() again.
5. Gather context safely: prefer safe_list_files() and search_in_files() for large projects.
"""

GET_CURRENT_DIRECTORY_DESCRIPTION = """Get current working directory.

Returns the process working directory as an absolute path.
Use this before file operations when you need to verify path resolution context."""

SAFE_RESOLVE_PATH_DESCRIPTION = """Resolve and validate a path inside the workspace.

Normalizes relative/absolute input and rejects traversal outside the workspace root.
Use this when you need a canonical workspace-relative path."""

LS_DESCRIPTION = """List direct entries in a directory (non-recursive).

Parameters:
- directory (optional, default='.')

Returns workspace-relative entries. Directories are suffixed with '/'.
Use this for quick orientation before deeper reads or edits."""

LIST_ALL_FILES_DESCRIPTION = """Recursively list all files under a directory.

Parameters:
- directory (optional, default='.')

Returns sorted workspace-relative file paths.
Useful for indexing, broad discovery, and context collection."""

SAFE_LIST_FILES_DESCRIPTION = """Recursively list files with safety filtering.

Parameters:
- directory (optional, default='.')
- max_file_size (optional)
- include_hidden (optional)

Skips ignored directories, binary files, and oversized files.
Prefer this when gathering context for LLM workflows."""

READ_FILE_DESCRIPTION = """Read complete UTF-8 text from a file.

Parameters:
- file_path (required)

Returns full file content as a single string.
Use before making edits to understand existing logic."""

READ_FILE_LINES_DESCRIPTION = """Read a bounded line range from a UTF-8 file.

Parameters:
- file_path (required)
- start (optional, 1-based)
- end (optional, inclusive)

Returns numbered lines and supports targeted inspection of large files."""

HEAD_FILE_DESCRIPTION = """Read the first N lines of a file.

Parameters:
- file_path (required)
- n (optional, default=50)

Returns numbered output for quick inspection of headers/imports/setup blocks."""

TAIL_FILE_DESCRIPTION = """Read the last N lines of a file.

Parameters:
- file_path (required)
- n (optional, default=50)

Returns numbered output useful for logs, summaries, and file endings."""

GET_FILE_TREE_DESCRIPTION = """Generate a deterministic directory tree view.

Parameters:
- directory (optional, default='.')
- indent_unit (optional)

Returns plain-text hierarchy with directories marked by '/'."""

BUILD_PROJECT_CONTEXT_DESCRIPTION = """Build a compact project context string.

Parameters:
- directory (optional, default='.')

Creates a bullet list of safe project files for prompt context assembly."""

WRITE_FILE_DESCRIPTION = """Create or overwrite a file with text content.

Parameters:
- file_path (required)
- content (required)
- overwrite (optional)
- create_dirs (optional)

Use for full rewrites or initial file generation."""

APPEND_FILE_DESCRIPTION = """Append text to an existing file or create one.

Parameters:
- file_path (required)
- content (required)
- create_dirs (optional)

Use for incremental additions such as logs, notes, or snippets."""

CREATE_FILE_DESCRIPTION = """Create an empty file.

Parameters:
- file_path (required)
- create_dirs (optional)
- overwrite (optional)

Useful for scaffolding placeholders before writing content."""

DELETE_FILE_DESCRIPTION = """Delete a file path.

Parameters:
- file_path (required)
- missing_ok (optional)

Use for cleanup of obsolete or temporary files."""

MAKE_DIRECTORY_DESCRIPTION = """Create a directory path.

Parameters:
- path (required)
- parents (optional)
- exist_ok (optional)

Creates single or nested directories."""

DELETE_DIRECTORY_DESCRIPTION = """Delete a directory path.

Parameters:
- path (required)
- recursive (optional)
- missing_ok (optional)

Supports empty deletion or recursive tree removal."""

COPY_FILE_DESCRIPTION = """Copy one file to another location.

Parameters:
- source (required)
- destination (required)
- overwrite (optional)
- create_dirs (optional)

If destination is a directory, source filename is preserved."""

MOVE_PATH_DESCRIPTION = """Move or rename a file/directory path.

Parameters:
- source (required)
- destination (required)
- overwrite (optional)
- create_dirs (optional)

Use for structural reorganization and path normalization."""

RENAME_PATH_DESCRIPTION = """Rename a path within its current parent directory.

Parameters:
- source (required)
- new_name (required, name only)
- overwrite (optional)

Rejects invalid names that include directory traversal."""

PATH_EXISTS_DESCRIPTION = """Check whether a path exists in the workspace.

Parameters:
- path (required)

Returns boolean result; invalid/outside-workspace paths return False."""

IS_FILE_DESCRIPTION = """Check whether a path is an existing file.

Parameters:
- path (required)

Returns False for missing paths, directories, or invalid paths."""

IS_DIR_DESCRIPTION = """Check whether a path is an existing directory.

Parameters:
- path (required)

Returns False for missing paths, files, or invalid paths."""

GET_FILE_INFO_DESCRIPTION = """Return filesystem metadata for a path.

Parameters:
- path (required)

Includes path type, size, timestamps, permissions, and access flags."""

FIND_FILES_DESCRIPTION = """Find files by glob pattern under a root directory.

Parameters:
- pattern (required)
- root (optional, default='.')

Matches both filename and workspace-relative path representations."""

SEARCH_IN_FILES_DESCRIPTION = """Search text across files under a root directory.

Parameters:
- query (required)
- root (optional, default='.')
- case_sensitive (optional)
- max_results (optional)

Returns file path, line number, and line preview for each match."""

REPLACE_IN_FILE_DESCRIPTION = """Replace text in a UTF-8 file and persist changes.

Parameters:
- file_path (required)
- old (required)
- new (required)
- count (optional)

Reports how many replacements were applied."""

COMPUTE_FILE_HASH_DESCRIPTION = """Compute file content hash.

Parameters:
- file_path (required)
- algorithm (optional, default='sha256')

Useful for integrity checks and content comparison."""

DIFF_FILES_DESCRIPTION = """Generate unified diff between two UTF-8 text files.

Parameters:
- file_a (required)
- file_b (required)
- context_lines (optional)

Use for review, validation, and change presentation."""

ZIP_PATHS_DESCRIPTION = """Create a zip archive from one or more paths.

Parameters:
- paths (required)
- output_zip (required)
- overwrite (optional)

Writes workspace-relative entries for reproducible archives."""

UNZIP_FILE_DESCRIPTION = """Extract a zip archive into a destination directory.

Parameters:
- zip_path (required)
- destination (optional, default='.')
- overwrite (optional)

Includes zip-slip protection and safe destination handling."""

__all__ = [
    "FILE_USAGE_INSTRUCTIONS",
    "GET_CURRENT_DIRECTORY_DESCRIPTION",
    "SAFE_RESOLVE_PATH_DESCRIPTION",
    "LS_DESCRIPTION",
    "LIST_ALL_FILES_DESCRIPTION",
    "SAFE_LIST_FILES_DESCRIPTION",
    "READ_FILE_DESCRIPTION",
    "READ_FILE_LINES_DESCRIPTION",
    "HEAD_FILE_DESCRIPTION",
    "TAIL_FILE_DESCRIPTION",
    "GET_FILE_TREE_DESCRIPTION",
    "BUILD_PROJECT_CONTEXT_DESCRIPTION",
    "WRITE_FILE_DESCRIPTION",
    "APPEND_FILE_DESCRIPTION",
    "CREATE_FILE_DESCRIPTION",
    "DELETE_FILE_DESCRIPTION",
    "MAKE_DIRECTORY_DESCRIPTION",
    "DELETE_DIRECTORY_DESCRIPTION",
    "COPY_FILE_DESCRIPTION",
    "MOVE_PATH_DESCRIPTION",
    "RENAME_PATH_DESCRIPTION",
    "PATH_EXISTS_DESCRIPTION",
    "IS_FILE_DESCRIPTION",
    "IS_DIR_DESCRIPTION",
    "GET_FILE_INFO_DESCRIPTION",
    "FIND_FILES_DESCRIPTION",
    "SEARCH_IN_FILES_DESCRIPTION",
    "REPLACE_IN_FILE_DESCRIPTION",
    "COMPUTE_FILE_HASH_DESCRIPTION",
    "DIFF_FILES_DESCRIPTION",
    "ZIP_PATHS_DESCRIPTION",
    "UNZIP_FILE_DESCRIPTION",
]
