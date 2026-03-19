# Utils Folder Guide

This folder contains the real operational rules of the project.

If `tools/` is the set of buttons the AI can press, `utils/` is the machinery that decides what those buttons actually do.

## Purpose

The purpose of this folder is to keep the important logic:

- reusable
- testable
- deterministic
- safer than prompt-only control

This is where the project enforces rules such as:

- stay inside the workspace
- keep plan state consistent
- allow only approved shell commands
- describe tools clearly enough for the AI to use them correctly

## Why This Folder Matters

AI agents become unreliable when too much behavior is hidden in prompt text alone.

This project avoids that by moving core rules into plain Python code.
That means behavior can be tested, reviewed, and reused outside the model loop.

## Folder Contents

### `files.py`

This file is the filesystem backbone of the project.

It supports:

- listing files and folders
- reading whole files or selected lines
- searching for text
- writing and appending content
- replacing text
- creating and deleting files or directories
- moving, renaming, and copying
- comparing files
- zipping and unzipping

Most important principle:

All paths are resolved against the repository workspace root.
If a path tries to escape outside the workspace, it is rejected.

That single design choice is one of the biggest safety features in the project.

### `plans.py`

This file is the plan system.

It creates and updates a markdown plan file that is:

- easy for a human to read
- easy for the code to parse

The trick is that the file contains two layers:

- a readable markdown summary at the top
- embedded JSON state at the bottom between marker comments

This lets the project keep one source of truth for both human visibility and machine updates.

This file handles:

- creating plans
- decomposing tasks into steps
- updating step status
- setting subgoals
- tracking progress
- recording reflections
- verifying and repairing plan files before a run starts

### `shell.py`

This file controls command-line execution.

It does not allow arbitrary shell access.

Instead, it validates:

- which command family is being used
- whether the working directory stays inside the allowed base path
- whether the output should be truncated
- whether timeouts are respected

Allowed command families are intentionally limited, including:

- `python` or `py`
- `pytest`
- `uv run`
- `ruff`
- selected read-only `git` subcommands

That means commands like destructive `git reset --hard` are blocked.

### `file_descriptions.py`

This file stores the explanatory text for file-related tools.

It may look simple, but it matters a lot because AI tools work best when:

- the purpose is obvious
- parameters are explained clearly
- safe usage patterns are described up front

Centralizing these descriptions also keeps `tools/file_tools.py` cleaner.

### `plan_descriptions.py`

This file does the same job for plan-related tools.

It tells the model:

- when to decompose work
- how to update plan state
- how to record progress and reflections

### `__init__.py`

This file is currently minimal, which is fine.
Its main role is package organization.

## Working Principles Used Across This Folder

### 1. Workspace First

Paths are resolved relative to the repository root.
Anything outside that root is rejected.

This reduces accidental damage and makes the system easier to reason about.

### 2. Human And Machine Compatibility

The project often stores state in a form that both humans and code can understand.

The best example is the plan file:

- humans read the markdown
- code reads the JSON block

### 3. Clear Error Messages

These utilities usually return readable error messages instead of crashing with raw stack traces.

That matters because the caller may be:

- an AI model
- the orchestrator
- the API layer
- a test

Readable failures make recovery and debugging much easier.

### 4. Thin AI Layer, Strong Python Layer

The project tries not to trust prompt text alone.

Instead:

- prompts describe the desired behavior
- utils enforce the real rules

### 5. Reuse Over Duplication

The same utility logic can be used by:

- the agent runtime
- the API
- direct Python imports
- tests

That reduces drift and hidden inconsistencies.

## The Plan File Design Is A Big Deal

For non-technical readers, this is one of the smartest parts of the project.

Why?

Normal tracking files are either:

- friendly for humans but hard for code to update
- friendly for code but ugly for humans

This project chooses both.

`plans.py` writes a file that looks like a readable checklist, but it also embeds JSON between markers so the software can safely reload and update the same file later.

That means:

- people can inspect progress manually
- the agent can resume with structured state
- corrupted or mismatched plan files can be repaired automatically

## The Shell Safety Design Is Also Important

Giving an AI terminal access can be risky.

This project reduces that risk by:

- allowlisting commands
- banning dangerous git actions
- limiting execution time
- scoping each command to a base directory
- truncating huge output

So shell access is treated as a controlled tool, not an unlimited superpower.

## When You Should Edit `utils/`

Edit this folder when you want to change:

- the true behavior of file operations
- how plans are stored or verified
- shell safety rules
- the tool-description text used by the AI

Do not start in `tools/` if the behavior problem is actually deeper.
`tools/` mainly exposes capabilities.
`utils/` defines what those capabilities really do.
