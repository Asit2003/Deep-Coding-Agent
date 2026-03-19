# Agent Folder Guide

This folder is the execution brain of the project.

If the repository were a small company, `agent/` would be the room where the manager, the worker instructions, the checklist format, and the final test step all live.

## Purpose

The purpose of this folder is to turn a human request into a controlled coding run.

It answers questions like:

- Where should the work happen?
- What instructions should the AI follow?
- How should progress be tracked?
- How do we run tests at the end?
- What shape should the result data have?

## What Really Runs Today

The most important file here is `orchestrator.py`.

That is the main production entry point used by the CLI and the API.
It builds a Deep Agent, hands it the approved tools, and returns a final summary after running tests.

The other agent files in this folder are still important, but they are better understood as supporting building blocks and reference implementations for a more explicitly staged workflow.

## Folder Contents

### `orchestrator.py`

This is the top-level manager.

Main jobs:

- turns a plain request into a safe project path
- verifies the plan file before work starts
- creates the Deep Agent with tools
- sends the user request to the model
- collects the final agent summary
- runs tests through `test_builder.py`
- returns a structured result

This file also contains helper logic for:

- deriving a project name from plain language
- normalizing working directories
- merging task results
- splitting independent vs dependent tasks

### `prompts.py`

This file stores the instruction text given to different AI roles.

Why that matters:

- prompts define the behavior standard
- keeping them in one file makes the system easier to tune
- it avoids scattering important instructions across the codebase

There are prompts for:

- the Deep Agent system role
- the planner role
- the coding role
- the reviewer role

### `state.py`

This file defines the shared data shapes used across the project.

In plain English, it says:

- what a task should look like
- what fields a full run result can contain

That helps the rest of the code stay consistent.

### `test_builder.py`

This file is the final inspection step.

It runs the configured test command in the chosen working directory and captures:

- whether tests passed
- the exit code
- the output text

The orchestrator uses this after the coding step.

### `planner_agent.py`

This file is a more explicit "planning specialist".

It can:

- inspect the project context
- ask the model for a task breakdown
- fall back to a local task decomposition if no model call is available
- save the plan to the markdown plan file
- set subgoals for the run

Important note:

This file is tested and useful, but the current top-level CLI/API flow does not call it directly.

### `coding_agent.py`

This file is a more explicit "task executor".

It defines a `DeepCodingAgent` that:

- exposes a set of file, shell, and planning tools to the model
- scopes file changes so they stay inside the project root
- loops through model tool calls
- returns structured task results

This is helpful because it shows what a lower-level agent loop looks like when you want tighter manual control.

Important note:

This is also not the main entry path used by `orchestrator.py` today.

### `reviewer.py`

This file is the quality-check specialist.

It can review:

- what tasks were attempted
- what results were reported
- whether tests ran successfully

It returns a verdict with:

- approval yes/no
- a summary
- issues
- next actions

Like the planner and coding worker, this is part of the repo's reusable building blocks rather than the main direct path used by the current orchestrator run.

### `__init__.py`

This file gives the package a simple import surface so users can do:

```python
from agent import CodingOrchestrator
```

instead of importing deeply from internal modules.

## How A Request Moves Through This Folder

1. A request enters through the CLI or API.
2. `orchestrator.py` checks configuration and plan-file readiness.
3. It decides the project name and working directory.
4. It builds a Deep Agent using the prompts and tool set.
5. The Deep Agent performs the coding work inside the allowed folder.
6. `test_builder.py` runs the test command.
7. The orchestrator packages the outcome into a final summary.

## Why This Folder Is Split Into Multiple Files

This split is deliberate:

- `orchestrator.py` handles the full run
- `prompts.py` holds model instructions
- `state.py` holds shared data contracts
- `test_builder.py` handles post-change validation
- `planner_agent.py`, `coding_agent.py`, and `reviewer.py` preserve explicit staged-agent logic for extension and experimentation

That separation makes the project easier to test, explain, and extend.

## Safety Principles In This Folder

- Working directories are normalized and blocked from escaping the repo.
- Missing OpenAI credentials stop the run early instead of failing later in a confusing way.
- Plan files are checked before the agent begins.
- The orchestrator always runs the configured test command after the agent finishes.
- Path scoping in `coding_agent.py` prevents accidental writes outside the intended project root.

## Most Important Things For A New Contributor To Understand

- `orchestrator.py` is the live center of gravity.
- Prompt quality matters because it changes agent behavior more than many code tweaks.
- The plan file is part of the product, not just a debug artifact.
- Tests are part of the delivery contract, not an optional extra.
- Not every module in this folder is on the current hot path, so always confirm whether you are changing the main runtime or a supporting component.

## If You Want To Change Behavior, Start Here

- Change request routing or project path decisions: `orchestrator.py`
- Change the AI's instructions: `prompts.py`
- Change result field definitions: `state.py`
- Change test execution behavior: `test_builder.py`
- Build a more staged multi-role flow: `planner_agent.py`, `coding_agent.py`, `reviewer.py`
