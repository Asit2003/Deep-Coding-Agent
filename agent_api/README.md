# API Folder Guide

This folder is the web-facing front door of the project.

If `agent/` is the engine room, `agent_api/` is the receptionist desk: it accepts requests, creates jobs, tracks their progress, and returns the final outcome in a clean HTTP format.

## Purpose

The purpose of this folder is to let other programs use the coding agent without touching the command line directly.

That means a website, dashboard, internal tool, or automation script can:

- submit a new coding request
- ask whether it is still running
- fetch the result later
- check whether the service is healthy

## Why This Matters

Without this folder, the project would only be useful to someone sitting at a terminal.

With this folder, the agent becomes a reusable service.

## The Simple Mental Model

Think of the API layer as a job queue with status tracking:

1. someone sends a request
2. the request is placed in a background worker queue
3. the real coding work happens in the orchestrator
4. the API remembers the status and result
5. the client asks for updates until the run is done

## Folder Contents

### `app.py`

This is the application factory.

Its job is to:

- configure logging
- create the FastAPI app
- attach the shared run manager
- register the routes
- shut down the worker manager when the app stops

This file answers the question, "How is the web service assembled?"

### `main.py`

This is the executable entry point for the API server.

It reads environment variables such as:

- `AGENT_API_HOST`
- `AGENT_API_PORT`
- `AGENT_API_RELOAD`
- `AGENT_API_LOG_LEVEL`

Then it starts Uvicorn.

### `service.py`

This is the most important file in the API folder.

It contains the background run manager.

Main responsibilities:

- create a unique run ID
- resolve the working directory safely
- build a per-run plan file path
- store run metadata in memory
- execute the orchestrator in a background thread
- update status from `queued` to `running` to `completed` or `failed`
- keep the final result for later retrieval

This file is what makes the API feel like a managed service instead of a simple one-shot function call.

### `schemas.py`

This file defines the request and response shapes using Pydantic models.

In practical terms, it decides:

- what fields clients are allowed to send
- what fields they will receive back
- what run statuses are valid

That keeps the API predictable and self-documenting.

### `dependencies.py`

This file is small but useful.

It gives route handlers access to the shared `AgentRunManager` stored on the FastAPI app.

### `logging.py`

This file configures process-wide logging one time.

It exists so that API events like queued runs, failures, and completions are visible in a consistent format.

### `routers/health.py`

This route answers a simple question:

"Is the service alive, and how busy is it?"

It returns:

- service status
- timestamp
- total runs tracked
- active runs

### `routers/runs.py`

This route file is the user-facing job API.

It provides:

- `POST /api/v1/agent/runs`
  Queue a new run
- `GET /api/v1/agent/runs/{run_id}`
  Fetch one run with its result
- `GET /api/v1/agent/runs`
  List recent runs

## How A Run Works Through The API

1. A client sends a POST request with a prompt.
2. The API validates the payload using `schemas.py`.
3. `service.py` creates a run record with a unique ID.
4. The run record is stored in memory with status `queued`.
5. A background thread starts the real orchestrator work.
6. The run becomes `running`.
7. The orchestrator finishes and returns a result.
8. The run becomes `completed`, and the result is stored.
9. If something breaks badly, the run becomes `failed`.

## What The Status Values Mean

- `queued`
  The request was accepted and is waiting for a worker.
- `running`
  The background worker is currently executing it.
- `completed`
  The background job finished and a result is available.
- `failed`
  The background worker crashed before it could finish cleanly.

Important detail:

`completed` does not always mean "the coding goal was perfect."
It means the background process finished.
To know whether the run truly succeeded, check `agent_success`.

## What `agent_success` Means

The API separates "the job finished" from "the job finished well."

`agent_success` becomes true only when the result looks healthy.
For the current orchestrator path, that mainly means:

- the run was not blocked during setup or execution
- the test stage passed

This is useful because a run can complete and still report that tests failed or setup was blocked.

## Where The Plan File Goes In API Runs

API runs do not all share one root `agent_plan.md`.

Instead, each run gets a dedicated plan file inside the target working directory:

`.deep-agent/runs/<run_id>/agent_plan.md`

This is important because background jobs may overlap, and each one needs its own checklist and progress log.

## Example API Usage

Start the service:

```bash
uv run deep-agent-api
```

Create a run:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/agent/runs ^
  -H "Content-Type: application/json" ^
  -d "{\"prompt\":\"Build a task tracking API\",\"working_directory\":\"project/task-api\"}"
```

Check one run:

```bash
curl http://127.0.0.1:8000/api/v1/agent/runs/<run_id>
```

List recent runs:

```bash
curl http://127.0.0.1:8000/api/v1/agent/runs
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Working Principles

- The API never performs the coding work directly.
  It delegates that job to the orchestrator from `agent/`.
- The API stores run state in memory.
  That keeps it simple but also means server restarts clear history.
- The API uses background threads, not a database-backed queue.
- Working directories are still validated through the same path-safety logic used by the core agent.

## Current Limitations

- No login or authentication
- No persistent database
- No multi-machine worker queue
- Run history disappears on restart
- This is best suited for local use or trusted internal environments

## When To Edit This Folder

- Add or change endpoints: edit `routers/`
- Change run tracking behavior: edit `service.py`
- Change request or response fields: edit `schemas.py`
- Change startup/server behavior: edit `main.py` or `app.py`
- Change logging format or level defaults: edit `logging.py`
