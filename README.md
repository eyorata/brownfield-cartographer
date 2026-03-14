# The Brownfield Cartographer

The Brownfield Cartographer is a Codebase Intelligence System designed for rapid Forward Deployed Engineer (FDE) onboarding. It ingests any GitHub repository or local path and creates a queryable knowledge graph of the system's architecture, data flows, and semantic structure.

## Installation

This project utilizes `uv` for fast dependency management. Make sure you have `uv` installed.

1. Clone this repository
2. Run `uv sync` to install dependencies
3. Activate the virtual environment

## Usage

### Analyze a Codebase
Run the core analysis pipeline on a given repository (local path or GitHub URL):

```bash
./.venv/Scripts/python.exe src/cli.py analyze /path/to/your/repo
```

You can also pass a GitHub URL (the CLI will shallow-clone it under `.cartography/_repos/`):

```bash
./.venv/Scripts/python.exe src/cli.py analyze https://github.com/dbt-labs/dbt-core
```

### Using paid LLM gateways (OpenRouter, etc.)
This tool speaks to any OpenAI-compatible API.

- Set `llm.base_url` to your provider’s base URL (e.g. OpenRouter: `https://openrouter.ai/api/v1`)
- Provide the API key either directly in `cartography_config.yaml` (`llm.api_key`) or via an env var:
  - `llm.api_key_env: "OPENROUTER_API_KEY"` and set `OPENROUTER_API_KEY=...`
- (Optional) OpenRouter attribution headers:
  - `llm.app_url` and `llm.app_name`

This runs the four-phase pipeline (Surveyor, Hydrologist, Semanticist, Archivist) and generates output artifacts in the *target repo's* `.cartography/` directory, including:
- `module_graph.json`: The layout and structure.
- `lineage_graph.json`: Data flow tracking.
- `CODEBASE.md`: A generated overview (graph summary + top modules).
- `onboarding_brief.md`: A generated Day-One-style brief (auto, based on graphs).
- `cartography_trace.jsonl`: Phase trace events.
- `semantic_index.json`: A semantic index (vector-searchable) containing module + function + class entries.

Optionally also write a second copy of artifacts elsewhere (useful for committing artifacts from this tool repo):

```bash
./.venv/Scripts/python.exe src/cli.py analyze .\\_targets\\dbt-core --output-dir .\\.cartography
```

### Query the Knowledge Graph
Once analysis is complete, you can interact with the graph.

```bash
./.venv/Scripts/python.exe src/cli.py query /path/to/analyzed/repo
```

`query` also accepts a GitHub URL and will clone it (useful if you analyzed a cloned repo previously and want to re-open it):

```bash
./.venv/Scripts/python.exe src/cli.py query https://github.com/dbt-labs/dbt-core
```

Example interactive commands:

- `stats`
- `sources 25`
- `sinks 25`
- `blast <dataset_or_node>`
- `trace up <node> 6`
- `trace down <node> 6`
- `module core/dbt/cli/main.py`

### Run The Local UI

```bash
./.venv/Scripts/python.exe src/cli.py serve --host 127.0.0.1 --port 8000
```

## Structure
- `src/agents/`: The intelligent agents (Surveyor, Hydrologist, etc.)
- `src/analyzers/`: Parse specific file types (Python AST, SQL lineage, etc.)
- `src/models/`: Core Pydantic data schemas representing graph nodes and edges
- `src/graph/`: NetworkX graph management and serialization
