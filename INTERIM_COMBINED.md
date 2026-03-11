# Interim Submission (Combined)

Date: 2026-03-11

This file combines `RECONNAISSANCE.md` (manual Day-One analysis) and `INTERIM_REPORT.md` (system status + artifacts) into a single markdown document for PDF conversion.

---

# RECONNAISSANCE.md (Interim)

Date: 2026-03-11

## Target Codebase (Qualifying)

Primary target: `dbt-labs/dbt-core` (local clone at `./_targets/dbt-core`)

Why this target qualifies for the rubric:

- Size: 1061+ files
- Languages: Python (`.py`), SQL/Jinja (`.sql`), YAML (`.yml`)
- Real production system: dbt Core CLI + execution engine used in production analytics workflows

Secondary targets (required for Cartography artifacts):

- `dbt-labs/jaffle_shop` (dbt project, SQL/YAML/CSV; local at `./_targets/jaffle_shop`)
- `eyorata/Roo-Code` (large TS monorepo with SQL migrations; local at `./_targets/Roo-Code`)

## The Five FDE Day-One Questions (Manual)

### 1) What is the primary ingestion path?

Interpretation for dbt-core: "ingestion" is the path from a user invocation + project files to executed SQL in a warehouse.

Manual trace (entry to execution):

- CLI entrypoint and programmatic runner live in `./_targets/dbt-core/core/dbt/cli/main.py`
  - `dbtRunner.invoke()` constructs a Click context and invokes the CLI.
  - The `@click.group(...)` CLI definition is in the same file.
- Preflight + manifest setup happen via `./_targets/dbt-core/core/dbt/cli/requires.py`
  - `setup_manifest()` calls `parse_manifest(...)` and installs the resulting `Manifest` into `ctx.obj["manifest"]`.
  - `setup_manifest()` is the bridging point where "project files on disk" become a normalized graph representation.
- Project parse + manifest writing live in `./_targets/dbt-core/core/dbt/parser/manifest.py`
  - `parse_manifest(...)` calls `ManifestLoader.get_full_manifest(...)`.
  - If `write_json` is enabled, `parse_manifest(...)` calls `write_manifest(manifest, runtime_config.project_target_path)`.
  - `write_manifest(...)` writes `manifest.json` (and also writes `semantic_manifest.json`).
- Command implementations are expressed as Tasks under `./_targets/dbt-core/core/dbt/task/`
  - `RunTask` is defined in `./_targets/dbt-core/core/dbt/task/run.py`
  - `CompileTask` is defined in `./_targets/dbt-core/core/dbt/task/compile.py`
  - `BuildTask` extends `RunTask` in `./_targets/dbt-core/core/dbt/task/build.py`
- Compilation output (compiled SQL on disk) is written by the Compiler in `./_targets/dbt-core/core/dbt/compilation.py`
  - `compile_node(...)` calls `_write_node(...)`
  - `_write_node(...)` uses `node.get_target_write_path(self.config.target_path, "compiled", ...)` and writes `compiled_code` under `target/compiled/...` in the dbt project.
- Execution results are written during graph/task execution in `./_targets/dbt-core/core/dbt/task/runnable.py`
  - On success paths where `self.args.write_json` is enabled, it writes `manifest.json` and then calls `result.write(self.result_path())` (e.g. `run_results.json`).

Observed pattern:

- "dbt the engine" ingests a dbt project (SQL models + YAML schema) into a Manifest, compiles it, and executes it.
  - Ingest: `core/dbt/cli/requires.py` -> `core/dbt/parser/manifest.py`
  - Compile: `core/dbt/compilation.py` writes compiled SQL into `target/compiled/`
  - Execute + report: `core/dbt/task/runnable.py` writes artifacts like `run_results.json` into `target/`

### 2) What are the critical output datasets/endpoints?

For dbt-core, there are two output classes:

1. Warehouse outputs (tables/views) created by running compiled SQL.
2. Local artifacts (JSON) that describe what happened and enable downstream tooling.

Local artifacts are explicitly named in `./_targets/dbt-core/core/dbt/constants.py`:

- `manifest.json` (a snapshot of the parsed/compiled project)
- `run_results.json` (execution results)
- `catalog.json` (docs data, if generated)
- `sources.json` (source freshness results)

Compiled SQL output is also material:

- Compiled SQL is written into the dbt project's `target/compiled/` directory via `./_targets/dbt-core/core/dbt/compilation.py` (`_write_node(...)`).

Key endpoint surfaces:

- CLI surface: `./_targets/dbt-core/core/dbt/cli/main.py`
- Artifact-writing path is referenced throughout the Task and parser docs (e.g. `./_targets/dbt-core/core/dbt/parser/README.md` mentions `target/manifest.json` as an output).

### 3) What is the blast radius of the most critical module?

Chosen "most critical module": compilation/execution pipeline, because it sits between parsed project definitions and warehouse side effects.

Manual signals:

- `./_targets/dbt-core/core/dbt/compilation.py` shows up in recent change velocity (see Q5), which is a strong proxy for "touches many features".
- Task graph suggests `CompileTask` and `RunTask` are central:
  - `./_targets/dbt-core/core/dbt/task/compile.py`
  - `./_targets/dbt-core/core/dbt/task/run.py`

Blast radius hypothesis:

- Changes in compilation / task execution can affect:
  - correctness of compiled SQL
  - what nodes are selected/run
  - emitted artifacts (manifest/run_results)
  - docs generation and downstream consumers that rely on manifest structure

### 4) Where is the business logic concentrated?

In a framework repo like dbt-core, "business logic" is the core behavior that users feel:

- CLI behavior and parameters:
  - `./_targets/dbt-core/core/dbt/cli/main.py`
  - `./_targets/dbt-core/core/dbt/cli/params.py` (also appears in velocity)
- Parsing and interpretation of dbt project structure:
  - `./_targets/dbt-core/core/dbt/parser/` (YAML readers, manifest construction)
- Task execution and orchestration:
  - `./_targets/dbt-core/core/dbt/task/`
- Compilation:
  - `./_targets/dbt-core/core/dbt/compilation.py`
- SQL/Jinja surface area that ships with dbt:
  - `./_targets/dbt-core/core/dbt/include/` contains starter projects and SQL/Jinja templates/macros.

### 5) What is the recent change velocity?

Method:

- Use `git log --since="30 days ago" --name-only` on the local clone and count file touches.

Observed (last 30 days in the local clone):

- 199 committed file touches (not unique files).
- Top touched files include:
  - `./_targets/dbt-core/core/hatch.toml`
  - `./_targets/dbt-core/tests/functional/semantic_models/test_semantic_model_v2_parsing.py`
  - `./_targets/dbt-core/tests/functional/semantic_models/fixtures.py`
  - `./_targets/dbt-core/core/dbt/compilation.py`
  - `./_targets/dbt-core/core/dbt/parser/schema_yaml_readers.py`
  - `./_targets/dbt-core/core/dbt/cli/params.py`

Interpretation:

- Work is concentrated in core compilation + schema parsing + CLI params, plus a lot of functional test changes.

## Difficulty Analysis (Manual)

Concrete pain points encountered during manual exploration:

- "Click-heavy" CLI layout: behavior is spread across decorators and shared global flags in `core/dbt/cli/main.py`, making call flow harder to follow top-to-bottom.
- Multiple "levels" of intent: CLI -> Task -> Parser/Manifest -> Compilation -> Adapter/Execution. It is easy to lose track of which layer owns a given behavior.
- SQL/Jinja is everywhere: many `.sql` files contain Jinja constructs (`{{ ref(...) }}`, `{% macro %}`, `{% test %}`, etc.), so naive SQL parsers fail without template awareness.
- Test fixtures look like real projects: `tests/functional/fixtures/...` contains "mini dbt projects" that expand the surface area of files that appear relevant.

How this informs Cartographer priorities:

- The tool should identify "central layers" (CLI, Tasks, Parser, Compilation) and provide a traceable path between them.
- SQL lineage needs Jinja-aware parsing (or a structured preprocessor) to avoid false negatives and odd edge labels.
- The tool should separate "product code" from "test fixtures" during mapping (or at least tag them), otherwise the map is dominated by tests.

## Cartographer Run (Evidence)

Command used:

```powershell
.\.venv\Scripts\python.exe .\src\cli.py analyze .\_targets\dbt-core
```

Artifacts produced (in the target repo):

- `./_targets/dbt-core/.cartography/module_graph.json` (701 module nodes, 158 edges)
- `./_targets/dbt-core/.cartography/lineage_graph.json` (40 nodes, 29 edges; partial and template-sensitive)

## Appendix: Small dbt Project (jaffle_shop) Manual Lineage

This repo is used as a sanity check for SQL lineage in an actual dbt project.

- `./_targets/jaffle_shop/models/staging/stg_customers.sql` reads `raw_customers`
- `./_targets/jaffle_shop/models/staging/stg_orders.sql` reads `raw_orders`
- `./_targets/jaffle_shop/models/staging/stg_payments.sql` reads `raw_payments`
- `./_targets/jaffle_shop/models/customers.sql` reads `stg_customers`, `stg_orders`, `stg_payments`
- `./_targets/jaffle_shop/models/orders.sql` reads `stg_orders`, `stg_payments`

Ingestion/outputs in the dbt project framing:

- Primary ingestion path (raw inputs): `./_targets/jaffle_shop/seeds/*.csv` loaded into the warehouse via `dbt seed`
- Critical outputs (analytics tables): `customers` and `orders` produced by `./_targets/jaffle_shop/models/customers.sql` and `./_targets/jaffle_shop/models/orders.sql`

---

# INTERIM_REPORT.md

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
