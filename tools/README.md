# Tools Folder Guide

This folder is the approved toolbox the AI is allowed to use.

In plain language, the files here answer this question:

"What actions can the agent perform while working on a coding task?"

## Purpose

The purpose of `tools/` is not to hold the deep logic itself.

Instead, this folder turns normal Python functions into model-callable tools.
That is a very important design choice.

Why?

- the AI needs a clean, well-described interface
- the real logic should stay testable and reusable
- safety checks should live below the AI layer, not only inside prompt text

So this folder acts as an adapter layer between the AI and the underlying utilities.

## The Big Difference Between `tools/` And `utils/`

- `tools/` says what the AI is allowed to call and how those actions are described.
- `utils/` contains the real implementation that actually performs the work.

Another way to say it:

- `tools/` is the control panel
- `utils/` is the wiring behind the wall

## Why This Separation Is Healthy

This split makes the project easier to maintain:

- the AI gets simple, well-labeled actions
- the real code stays reusable from tests and non-AI code
- safety logic stays in normal Python, where it is easier to verify
- changing a tool description does not always require changing the underlying logic

## Folder Contents

### `file_tools.py`

This file exposes file and directory operations as LangChain tools.

Examples of what it makes available:

- list files
- read files
- read selected lines
- search inside files
- write files
- append files
- replace text
- create folders
- copy, move, rename, zip, and unzip

Important detail:

The descriptions shown to the AI are not written inline here.
They are mostly imported from `utils/file_descriptions.py`.

### `plan_tools.py`

This file exposes planning operations as tools.

These tools let the AI:

- create a plan
- update plan step status
- break work into smaller steps
- store subgoals
- log progress
- reflect on what happened

The real plan behavior lives in `utils/plans.py`.

### `research_tools.py`

This file provides local discovery helpers.

Despite the name "research", these tools search the local repository and the `Docs/` folder.
They are not internet search tools.

That means the agent can:

- list documentation files
- search notes in `Docs/`
- search the project for implementation clues

This is useful when the model needs context but should stay grounded in local source material.

### `todo_tools.py`

This file treats the markdown plan file like a lightweight todo list.

It gives the agent a higher-level way to:

- read plan status at a glance
- list open steps
- mark a step completed
- mark a step blocked

These are convenience tools built on top of the deeper plan-state system.

### `shell_tools.py`

This file exposes a controlled shell command tool.

It does not give the AI free command-line power.

Instead, it creates a scoped `run_shell` tool that:

- stays inside a chosen base directory
- uses the safety rules from `utils/shell.py`
- only allows approved command families

That makes shell access useful without making it reckless.

### `__init__.py`

This package marker exists mainly to keep the folder importable as a clean Python package.

## How Tools Are Built

The general pattern in this folder is:

1. import the underlying function from `utils/`
2. wrap it with `@tool`
3. give it a strong description
4. export it so the agent can use it

That description step matters more than it may seem.
Well-written tool descriptions help the model choose the right action at the right time.

## Why Tool Descriptions Matter So Much

An AI model does not "understand" a tool the way a human engineer reads code.
It mostly understands:

- the tool name
- the parameter schema
- the description text

So the project stores rich, explicit descriptions to make the agent more reliable.

## Working Principles In This Folder

- Keep wrappers thin.
- Keep real logic in `utils/`.
- Use clear descriptions.
- Prefer structured inputs and outputs.
- Scope powerful actions like shell access to a safe directory.

## Safety Philosophy

This folder supports safe AI behavior in several ways:

- file operations eventually pass through workspace path guards
- plan tools operate on a controlled markdown-plus-JSON state format
- shell tools use allowlists and reject dangerous git operations
- research tools are local and grounded

## If You Want To Add A New Capability

The usual path is:

1. add or update the real logic in `utils/`
2. write a clear description for the AI
3. expose it from `tools/`
4. add tests to prove the behavior and safety

This keeps the system understandable and reduces hidden behavior.

## Who Should Change This Folder

Edit `tools/` when you want to change:

- what the AI can call
- how a tool is described to the AI
- how a tool is grouped and exposed

Edit `utils/` instead when you want to change:

- the real file, plan, or shell logic
- validation rules
- security behavior
- low-level implementation details
