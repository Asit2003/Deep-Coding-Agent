# Deep Coding Agent

OpenAI-only coding agent built on LangChain Deep Agents.

Execution model:
- Preflight-verify plan file state.
- Derive concept-based project directory under `AGENT_PROJECTS_ROOT`.
- Run a Deep Agent with filesystem + planning/research tools.
- Run configured tests and emit final summary.

## Model Backend (OpenAI only)

Set environment variables:

- `AGENT_TEMPERATURE` (default: `0.1`)
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (default: `gpt-5-mini`)
- `OPENAI_BASE_URL` (default: `https://api.openai.com/v1`)

## Run

```bash
deep-agent "Implement feature X with tests"
```

The agent creates/uses an output directory at `project/<project-name>` for generated
implementation files. You can pass an explicit name:

```bash
deep-agent "Implement feature X with tests" --project-name feature-x
```

Or from Python:

```python
from agent import CodingOrchestrator

orchestrator = CodingOrchestrator()
result = orchestrator.run("Implement feature X with tests")
print(result["final_summary"])
```

You can also target a specific workspace directory:

```bash
deep-agent "Implement feature X with tests" --working-directory apps/feature-x
```

## API

Start the FastAPI service:

```bash
deep-agent-api
```

Create a run:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/agent/runs \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"Build a FastAPI endpoint\",\"working_directory\":\"project/api-demo\"}"
```

Check run status:

```bash
curl http://127.0.0.1:8000/api/v1/agent/runs/<run_id>
```
