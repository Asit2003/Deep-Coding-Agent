"""LangChain tool bindings for filesystem operations.

All concrete file logic lives in `utils/files.py`. This module only exposes
those functions as `@tool` instances with detailed descriptions.
"""

from langchain_core.tools import tool
from utils import files as file_ops
from utils.file_descriptions import (
    APPEND_FILE_DESCRIPTION,
    BUILD_PROJECT_CONTEXT_DESCRIPTION,
    COMPUTE_FILE_HASH_DESCRIPTION,
    COPY_FILE_DESCRIPTION,
    CREATE_FILE_DESCRIPTION,
    DELETE_DIRECTORY_DESCRIPTION,
    DELETE_FILE_DESCRIPTION,
    DIFF_FILES_DESCRIPTION,
    FILE_USAGE_INSTRUCTIONS,
    FIND_FILES_DESCRIPTION,
    GET_CURRENT_DIRECTORY_DESCRIPTION,
    GET_FILE_INFO_DESCRIPTION,
    GET_FILE_TREE_DESCRIPTION,
    HEAD_FILE_DESCRIPTION,
    IS_DIR_DESCRIPTION,
    IS_FILE_DESCRIPTION,
    LIST_ALL_FILES_DESCRIPTION,
    LS_DESCRIPTION,
    MAKE_DIRECTORY_DESCRIPTION,
    MOVE_PATH_DESCRIPTION,
    PATH_EXISTS_DESCRIPTION,
    READ_FILE_DESCRIPTION,
    READ_FILE_LINES_DESCRIPTION,
    RENAME_PATH_DESCRIPTION,
    REPLACE_IN_FILE_DESCRIPTION,
    SAFE_LIST_FILES_DESCRIPTION,
    SAFE_RESOLVE_PATH_DESCRIPTION,
    SEARCH_IN_FILES_DESCRIPTION,
    TAIL_FILE_DESCRIPTION,
    UNZIP_FILE_DESCRIPTION,
    WRITE_FILE_DESCRIPTION,
    ZIP_PATHS_DESCRIPTION,
)

_TOOL_SPECS = [
    (
        "get_current_directory",
        GET_CURRENT_DIRECTORY_DESCRIPTION,
    ),
    ("safe_resolve_path", SAFE_RESOLVE_PATH_DESCRIPTION),
    ("list_files", LS_DESCRIPTION),
    ("list_all_files", LIST_ALL_FILES_DESCRIPTION),
    ("safe_list_files", SAFE_LIST_FILES_DESCRIPTION),
    ("read_file", READ_FILE_DESCRIPTION),
    ("read_file_lines", READ_FILE_LINES_DESCRIPTION),
    ("head_file", HEAD_FILE_DESCRIPTION),
    ("tail_file", TAIL_FILE_DESCRIPTION),
    ("get_file_tree", GET_FILE_TREE_DESCRIPTION),
    (
        "build_project_context",
        BUILD_PROJECT_CONTEXT_DESCRIPTION,
    ),
    ("write_file", WRITE_FILE_DESCRIPTION),
    ("append_file", APPEND_FILE_DESCRIPTION),
    ("create_file", CREATE_FILE_DESCRIPTION),
    ("delete_file", DELETE_FILE_DESCRIPTION),
    ("make_directory", MAKE_DIRECTORY_DESCRIPTION),
    ("delete_directory", DELETE_DIRECTORY_DESCRIPTION),
    ("copy_file", COPY_FILE_DESCRIPTION),
    ("move_path", MOVE_PATH_DESCRIPTION),
    ("rename_path", RENAME_PATH_DESCRIPTION),
    ("path_exists", PATH_EXISTS_DESCRIPTION),
    ("is_file", IS_FILE_DESCRIPTION),
    ("is_dir", IS_DIR_DESCRIPTION),
    ("get_file_info", GET_FILE_INFO_DESCRIPTION),
    ("find_files", FIND_FILES_DESCRIPTION),
    ("search_in_files", SEARCH_IN_FILES_DESCRIPTION),
    ("replace_in_file", REPLACE_IN_FILE_DESCRIPTION),
    ("compute_file_hash", COMPUTE_FILE_HASH_DESCRIPTION),
    ("diff_files", DIFF_FILES_DESCRIPTION),
    ("zip_paths", ZIP_PATHS_DESCRIPTION),
    ("unzip_file", UNZIP_FILE_DESCRIPTION),
]

for _name, _description in _TOOL_SPECS:
    globals()[_name] = tool(
        description=_description, parse_docstring=True
    )(getattr(file_ops, _name))


__all__ = [
    "FILE_USAGE_INSTRUCTIONS",
    *[name for name, _ in _TOOL_SPECS],
]
