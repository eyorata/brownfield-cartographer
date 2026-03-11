# The Brownfield Cartographer - Interim Report

## Phase 0: Reconnaissance

### Manual Day-One Analysis (Qualifying Target)
Primary target for manual reconnaissance: `dbt-labs/dbt-core` (local clone at `./_targets/dbt-core`).

Why this target qualifies for the rubric:

- 1061+ files
- Python + SQL/Jinja + YAML present
- Real production system (dbt Core CLI + compilation/execution pipeline)

Full manual Day-One analysis is captured in `RECONNAISSANCE.md` and explicitly answers the five FDE Day-One questions with concrete file paths and a difficulty analysis.

---

## Architecture Diagram (Progress Snapshot)

```mermaid
graph TD
    INPUT[Target Repo (local path or GitHub URL)] --> CLI[src/cli.py]
    CLI -->|analyze| ORCH[src/orchestrator.py]

    ORCH --> SURV[Surveyor]
    ORCH --> HYDRO[Hydrologist]
    ORCH --> SEM[Semanticist (planned)]
    ORCH --> ARC[Archivist (planned)]
    
    SURV --> KG[(Knowledge Graph)]
    HYDRO --> KG
    SEM --> KG
    ARC --> KG
    
    SURV -->|ModuleNodes + import graph + PageRank + git velocity| KG
    HYDRO -->|Lineage edges (SQL + dbt YAML sources)| KG
    SEM -->|Purpose statements + doc drift (not started)| KG
    ARC -->|CODEBASE.md + onboarding brief (not started)| KG
    
    KG -->|Serialize| MJSON[.cartography/module_graph.json]
    KG -->|Serialize| LJSON[.cartography/lineage_graph.json]
    KG -->|Serialize (planned)| CODEBASE[.cartography/CODEBASE.md]
    KG -->|Serialize (planned)| BRIEF[.cartography/onboarding_brief.md]
```

---

## Progress Summary
### Working (Falsifiable)

- CLI: `src/cli.py` supports `analyze` and accepts a local path (and GitHub URL cloning support is implemented).
- Orchestration: `src/orchestrator.py` runs Surveyor then Hydrologist and writes artifacts into the *target repo's* `.cartography/` directory.
- Models: `src/models/nodes.py` and `src/models/edges.py` define Pydantic schemas used by agents.
- Module map (Surveyor): `src/agents/surveyor.py`
  - Adds module nodes for `.py`, `.sql`, `.yml`, `.yaml`
  - Adds Python import edges only when the imported module exists locally
  - Computes PageRank via a pure-Python power iteration implementation (no numpy dependency)
  - Extracts git velocity via `git log --since="N days ago"` (best-effort; safe.directory handled)
- Lineage (Hydrologist): `src/agents/hydrologist.py`
  - Extracts SQL lineage using `src/analyzers/sql_lineage.py` (sqlglot when possible; regex fallback for dbt Jinja `ref()` / `source()`)
  - Extracts dbt source definitions from schema-style YAML via `src/analyzers/dag_config_parser.py`
- Serialization: `src/graph/knowledge_graph.py` writes valid NetworkX node-link JSON for both graphs.

### In Progress / Partial

- `src/analyzers/tree_sitter_analyzer.py`
  - Python parsing uses stdlib `ast` fallback for robustness.
  - Tree-sitter LanguageRouter exists but SQL/YAML AST extraction is not implemented yet.
- `query` mode: `src/cli.py query` is a stub (Navigator agent not implemented).

### Not Started (Final-only components)

- Semanticist agent (purpose statements, doc drift, domain clustering)
- Archivist agent (CODEBASE.md, onboarding brief, trace logs)

---

## Early Accuracy Observations
### Target: `dbt-labs/jaffle_shop` (dbt project sanity check)

- Manual expectation:
  - `models/customers.sql` depends on `models/staging/stg_customers.sql`, `models/staging/stg_orders.sql`, `models/staging/stg_payments.sql`.
  - `models/orders.sql` depends on `models/staging/stg_orders.sql`, `models/staging/stg_payments.sql`.
- Generated lineage graph (from `./_targets/jaffle_shop/.cartography/lineage_graph.json`):
  - Correctly captures `models/customers.sql` consuming `stg_customers`, `stg_orders`, `stg_payments` and producing `customers`.
  - Correctly captures `models/staging/stg_orders.sql` consuming `raw_orders` and producing `stg_orders`.

### Target: `dbt-labs/dbt-core` (qualifying target)

- Generated module graph (from `./_targets/dbt-core/.cartography/module_graph.json`):
  - Produces a non-empty graph (701 nodes, 158 edges), and includes central paths like `core/dbt/cli/main.py` and `core/dbt/task/*` as nodes.
- Generated lineage graph (from `./_targets/dbt-core/.cartography/lineage_graph.json`):
  - Correctly captures starter-project ref dependency: `my_second_dbt_model.sql` consumes `my_first_dbt_model`.
  - Incorrect edge label example: a multi-arg `ref('test','a')` pattern currently yields a malformed source string in the lineage graph (regex limitation).

Likely causes of misses/inaccuracies:

- SQL models contain Jinja constructs, so sqlglot parsing often fails and we rely on regex fallback which does not fully normalize all dbt ref() call shapes.

---

## Known Gaps & Plan for Final Submission
### Known Gaps (Interim)

- No Navigator (`query`) implementation yet (so no interactive blast-radius/trace queries).
- No Semanticist/Archivist agents yet (so no `CODEBASE.md` or onboarding brief generation).
- Lineage is partial and template-sensitive (dbt Jinja is not fully parsed; regex fallback can mislabel edges for some patterns).
- Module graph for SQL/YAML-only repos does not yet include explicit file-to-file dependency edges (those edges currently live in the lineage graph).

### Sequenced Plan (Final)

1. Add Navigator query mode (critical path)
   - Implement basic CLI loop and 3 core queries: `trace_lineage`, `blast_radius`, `find_sources/find_sinks`.
   - Dependency: lineage graph needs stable dataset naming normalization.
2. Improve dbt-aware lineage normalization (critical path)
   - Parse `ref()` with 1 or 2 args; normalize to model name.
   - Tag nodes as "model", "seed", "source" using directory structure + YAML schema.
3. Add Semanticist (LLM purpose statements + doc drift) (high risk, iterative)
   - Risk: prompt quality and grounding will require iteration.
   - Fallback: ship purpose statements only for top-ranked modules if time runs short.
4. Add Archivist (CODEBASE.md + onboarding brief + trace log) (depends on 1-3)
   - Generate `CODEBASE.md` from KG + purpose statements + key paths.
   - Generate onboarding brief by answering the 5 Day-One questions with citations.
5. Incremental update mode (stretch)
   - Use `git diff` to re-analyze changed files only; maintain `.cartography/cartography_trace.jsonl`.

If time runs short:

- Prioritize (1) + (2) + (4) minimal, and defer clustering + incremental update.
