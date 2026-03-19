# Deep Coding Agent

Deep Coding Agent is a local AI coding assistant that turns a plain-English request into a small, structured coding workflow.

In simple terms, you tell it what software you want, it chooses a safe working folder, keeps a running checklist, edits files through controlled tools, runs tests, and gives you a summary of what happened.

## Why This Project Exists

Many AI coding demos feel impressive for a minute, but they become hard to trust because they:

- edit files without a clear plan
- lose track of progress
- mix work from different requests
- run risky commands too freely
- finish without proving anything works

This project exists to make an agent behave more like a careful teammate:

- it keeps a plan file
- it works inside a chosen project folder
- it uses restricted tools instead of unrestricted access
- it runs tests after making changes
- it exposes both a command-line interface and an HTTP API

## The Big Idea In Plain English

If you are non-technical, it helps to imagine the system like this:

- You are the client giving a job.
- The `agent/` folder is the manager and execution brain.
- The `tools/` folder is the approved toolbox the AI can hold.
- The `utils/` folder is the real machinery behind those tools.
- The `agent_api/` folder is the front desk for web/API access.
- The plan file is the job checklist.
- The test runner is the final quality check.

## What Happens During One Run

1. You send a request, such as "Build a FastAPI service with tests".
2. The app loads settings from `.env`.
3. It verifies that a plan file exists and matches the request.
4. It decides where the work should happen.
   By default this is under `project/<derived-name>`.
5. It creates a Deep Agent with safe tools for files, planning, local research, todo tracking, and limited shell commands.
6. The agent reads and edits files inside the chosen working directory.
7. The configured test command runs.
8. A final summary is returned.

## Project Structure

- `agent/`
  Core execution logic. This is where the orchestrator, prompts, state models, and test runner live.
- `agent_api/`
  FastAPI service that lets other apps create and monitor runs over HTTP.
- `tools/`
  Tool wrappers that the agent can call.
- `utils/`
  Reusable low-level logic for files, plan handling, shell safety, and tool descriptions.
- `tests/`
  Automated checks for path safety, plan behavior, API behavior, orchestrator behavior, and shell restrictions.
- `Docs/`
  Project notes and high-level design documents.
- `project/`
  Local generated workspaces created by the agent. This folder is git-ignored on purpose.

## Important Note About The Current Architecture

The main live execution path today is centered around `agent/orchestrator.py`.

That file builds a Deep Agent from the `deepagents` package and gives it a controlled set of tools.

This repository also contains `planner_agent.py`, `coding_agent.py`, and `reviewer.py`.
Those files are useful building blocks and are covered by tests, but they are not the primary production path used by the current CLI/API flow.

## Beginner-Friendly Glossary

- Agent: an AI worker that tries to complete a task.
- Orchestrator: the part that sets up and supervises the run.
- API: a web interface that other programs can call.
- Tool: an action the AI is allowed to perform, such as reading a file.
- Utility: the underlying Python logic behind a tool.
- Plan file: a markdown checklist that stores progress and machine-readable state.
- Working directory: the folder where the current request is allowed to make changes.

## Getting Started

### 1. Install Requirements

Recommended:

```bash
uv sync --dev
```

If you do not use `uv`, you can install from the requirement files manually, but the repo is clearly set up around `uv`.

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your OpenAI key.

Most important values:

- `OPENAI_API_KEY`
  Required. Without this the agent will refuse to run.
- `OPENAI_MODEL`
  OpenAI model name. Default is `gpt-5-mini`.
- `OPENAI_BASE_URL`
  Usually `https://api.openai.com/v1`.
- `AGENT_TEMPERATURE`
  Controls randomness. Lower values make output steadier.
- `AGENT_PROJECTS_ROOT`
  Default folder for generated workspaces. Default is `project`.
- `AGENT_PLAN_FILE`
  Default CLI plan file. Default is `agent_plan.md`.
- `AGENT_TEST_COMMAND`
  Command used after coding. Default is `uv run pytest -q`.
- `PLANNING_MAX_STEPS`
  Maximum number of steps used when a plan is auto-created.
- `MAX_TOOL_ROUNDS`
  Maximum number of tool-calling rounds the agent can take in one task loop.
- `MAX_PARALLEL_TASKS`
  Maximum parallel workers for the explicit task runner components.

Advanced note:

- `MAX_GRAPH_ITERATIONS` exists in configuration for broader orchestration control, but it is not the main knob you usually need to care about in the current top-level flow.

## How To Run It

### Command Line

Run with an automatically derived project name:

```bash
uv run deep-agent "Build a FastAPI endpoint with tests"
```

Run with your own project name:

```bash
uv run deep-agent "Build a FastAPI endpoint with tests" --project-name customer-api
```

Run inside a specific existing folder:

```bash
uv run deep-agent "Improve the backend and add tests" --working-directory project/customer-api
```

### Python Usage

```python
from agent import CodingOrchestrator

orchestrator = CodingOrchestrator()
result = orchestrator.run("Implement feature X with tests")
print(result["final_summary"])
```

### HTTP API

Start the API:

```bash
uv run deep-agent-api
```

Create a run:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/agent/runs ^
  -H "Content-Type: application/json" ^
  -d "{\"prompt\":\"Build a FastAPI endpoint\",\"working_directory\":\"project/api-demo\"}"
```

Check status:

```bash
curl http://127.0.0.1:8000/api/v1/agent/runs/<run_id>
```

## Where Files Get Created

There are two common patterns:

- CLI runs normally use the root-level `agent_plan.md` unless you override `AGENT_PLAN_FILE`.
- API runs create a run-specific plan file inside the target working directory:
  `.deep-agent/runs/<run_id>/agent_plan.md`

Generated application code usually goes into:

- `project/<derived-project-name>/`

unless you explicitly pass `--working-directory` or API `working_directory`.

## Safety And Guardrails

This project is intentionally not a free-for-all.

Key protections include:

- Paths are checked so the agent cannot wander outside the repository workspace.
- Shell commands are allowlisted.
- Destructive git commands are blocked.
- Plan files are verified and repaired when possible before a run starts.
- The API gives each run its own plan file so background jobs do not overwrite one another.
- Tests are run after the coding step.

## What The Plan File Really Is

The plan file is designed for both humans and machines:

- the top part is readable markdown
- the bottom part contains embedded JSON between comment markers

That means a person can open the file and understand the checklist, while the code can also load the exact same file and update structured state safely.

## What This Project Is Good At

- controlled local coding experiments
- repeatable agent runs inside a chosen folder
- simple API-based automation
- plan-driven file editing
- test-after-change workflows

## Current Limitations

- OpenAI is the only active model provider in the current runtime.
- API run history is stored in memory, so server restarts clear it.
- The system does not yet include authentication, user accounts, or persistent database storage.
- Some supporting agent modules are present as reusable building blocks, but the main production path is more direct and simpler.

## Read The Folder Guides Next

- [`agent/README.md`](agent/README.md)
- [`agent_api/README.md`](agent_api/README.md)
- [`tools/README.md`](tools/README.md)
- [`utils/README.md`](utils/README.md)
