# onboarding_brief.md

Generated: 2026-03-14T09:27:55Z
Target repo: C:\Users\user\Documents\brownfield-cartographer\brownfield-cartographer

## Day-One Questions (Semanticist)

---

## Day-One Questions (Auto)

### 1) What does this system do?
- This repo was analyzed into a module graph (structure) and a lineage graph (data dependencies).

### 2) What are critical outputs?
- Outputs: `.cartography/module_graph.json`, `.cartography/lineage_graph.json`, `.cartography/CODEBASE.md`.

### 3) What are likely data sources/sinks?
- Sources (in-degree 0 datasets):
- Sinks (out-degree 0 datasets):

### 4) What are high-leverage modules?
- Top PageRank modules (structural centrality):
  - src/llm/openai_compat.py (pagerank=0.068901)
  - cartography_config.yaml (pagerank=0.037244)
  - main.py (pagerank=0.037244)
  - src/cli.py (pagerank=0.037244)
  - src/config.py (pagerank=0.037244)
  - src/orchestrator.py (pagerank=0.037244)
  - src/ui_server.py (pagerank=0.037244)
  - src/__init__.py (pagerank=0.037244)
  - src/agents/archivist.py (pagerank=0.037244)
  - src/agents/hydrologist.py (pagerank=0.037244)

### 5) What changed recently?
- Top changed files (30d):
  - src/orchestrator.py (touches=12)
  - src/cli.py (touches=11)
  - src/agents/hydrologist.py (touches=9)
  - src/agents/surveyor.py (touches=8)
  - src/analyzers/sql_lineage.py (touches=7)
  - src/agents/semanticist.py (touches=6)
  - src/analyzers/tree_sitter_analyzer.py (touches=6)
  - .gitignore (touches=6)
  - src/analyzers/dag_config_parser.py (touches=5)
  - README.md (touches=4)

