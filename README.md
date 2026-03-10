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
python src/cli.py analyze /path/to/your/repo
```

This will run the sequence of analysis agents and generate output artifacts in the `.cartography/` directory, including:
- `module_graph.json`: The layout and structure.
- `lineage_graph.json`: Data flow tracking.
- `CODEBASE.md`: High-level AI context map.

### Query the Knowledge Graph
Once analysis is complete, you can interact with the graph.

```bash
python src/cli.py query /path/to/analyzed/repo
```

## Structure
- `src/agents/`: The intelligent agents (Surveyor, Hydrologist, etc.)
- `src/analyzers/`: Parse specific file types (Python AST, SQL lineage, etc.)
- `src/models/`: Core Pydantic data schemas representing graph nodes and edges
- `src/graph/`: NetworkX graph management and serialization
