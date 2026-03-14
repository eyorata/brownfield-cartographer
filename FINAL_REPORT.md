# Final Report -- Sunday March 15, 03:00 UTC

Project: The Brownfield Cartographer

## Single PDF Report Contents
This report contains:
- RECONNAISSANCE: manual Day-One analysis vs. system-generated output comparison
- Architecture diagram of the four-agent pipeline (finalized)
- Accuracy analysis: which Day-One answers were correct, which were wrong, and why
- Limitations: what the Cartographer fails to understand, what remains opaque
- FDE Applicability: how to use the tool in a real client engagement
- Self-audit results (Cartographer run on Week 1 repo, discrepancies explained)

## 1) RECONNAISSANCE vs System Output (dbt-core)

Manual reconnaissance summary: All five Day-One questions were answered with concrete file paths, module references, and artifacts. The difficulty analysis identifies concrete obstacles (CLI indirection, multi-layer execution, Jinja templating, and test fixture noise) and links them to system priorities (traceable path across layers, template-aware lineage, and de-emphasizing test fixtures).

### Q1) Primary ingestion path
Manual (RECONNAISSANCE.md):
- dbt CLI entrypoint -> manifest setup -> manifest parse/write -> task execution -> compilation -> run results.
- Key modules: `core/dbt/cli/main.py`, `core/dbt/cli/requires.py`, `core/dbt/parser/manifest.py`, `core/dbt/task/*`, `core/dbt/compilation.py`, `core/dbt/task/runnable.py`.

System (onboarding_brief.md):
- Auto section only: "This repo was analyzed into a module graph (structure) and a lineage graph (data dependencies)."
- Best available system signal: the system confirms graph construction but does not specify the dbt ingestion path.

Assessment:
- Partially correct. The system established structural and lineage graphs but did not identify the ingestion path.
- Root cause: Semanticist Day-One answers did not run for this target; Archivist auto text is generic.

### Q2) Critical outputs
Manual (RECONNAISSANCE.md):
- Warehouse outputs (tables/views) plus local artifacts: `manifest.json`, `run_results.json`, `catalog.json`, `sources.json`.
- Compiled SQL in `target/compiled/`.

System (onboarding_brief.md):
- "Outputs: `.cartography/module_graph.json`, `.cartography/lineage_graph.json`, `.cartography/CODEBASE.md`."

Assessment:
- Partially correct. The system reported Cartographer artifacts, but did not surface dbt-core warehouse outputs or runtime artifacts.
- Root cause: Archivist auto section summarizes Cartographer outputs, not dbt-core domain outputs.

### Q3) Blast radius of the most critical module
Manual (RECONNAISSANCE.md):
- Compilation/execution pipeline is most critical.
- Changes can affect compiled SQL correctness, selected nodes, emitted artifacts, and downstream tooling.

System (onboarding_brief.md):
- Auto section lists sources/sinks only.
- Sources (in-degree 0 datasets): `seed`, `seed_source.seed`, `my_source.my_table`
- Sinks (out-degree 0 datasets): `my_second_dbt_model`, `b`, `b_root_package_in_ref`, `model`, `incremental`, `metricflow_time_spine`, `metricflow_time_spine_second`, `model_to_unit_test`, `model_with_lots_of_schema_configs`, `snapshot_source`, `inner`

Assessment:
- Partially correct. The system surfaced lineage sources/sinks but did not describe the blast radius of the critical module.
- Root cause: Hydrologist captures lineage datasets but does not map critical-module failure impact across the module graph in the Day-One brief.

### Q4) Business logic concentration
Manual (RECONNAISSANCE.md):
- CLI entrypoints, parser/manifest construction, task execution, compilation, include/ macros.

System (onboarding_brief.md):
- "High-leverage modules" listed by PageRank (dominated by test fixtures).
- Examples: `tests/unit/utils/__init__.py`, `tests/functional/snapshots/fixtures.py`, `tests/functional/defer_state/fixtures.py`, `tests/functional/graph_selection/fixtures.py`, `tests/functional/partial_parsing/fixtures.py`, `core/dbt/graph/graph.py`, `core/dbt/config/renderer.py`.

Assessment:
- Partially correct. It identifies central modules by PageRank, but business-logic concentration is obscured by test fixture density.
- Root cause: Surveyor PageRank treats tests and fixtures as first-class nodes; there is no domain-aware weighting or test de-prioritization.

### Q5) Recent change velocity
Manual (RECONNAISSANCE.md):
- Top touched files: `core/hatch.toml`, semantic model tests, `core/dbt/compilation.py`, `core/dbt/parser/schema_yaml_readers.py`, `core/dbt/cli/params.py`.

System (onboarding_brief.md):
- Top changed files list includes `core/dbt/compilation.py` and `core/dbt/cli/params.py`, plus CI/workflow files like `.github/workflows/main.yml`.

Assessment:
- Mostly correct. It surfaces several of the same high-velocity files, but lacks interpretive context and includes CI/workflow files.
- Root cause: Surveyor velocity uses raw git touches and does not filter meta/CI paths.

## 2) Architecture Diagram (Finalized, Mermaid.js)
```mermaid
flowchart LR
  A[Input Repo\n(GitHub URL or local path)]
  S[Surveyor\nmodule graph, PageRank, git velocity, dead code]
  H[Hydrologist\nlineage graph, sources/sinks, blast radius]
  M[Semanticist\npurpose statements, doc drift,\nsemantic index, Day-One answers]
  R[Archivist\nCODEBASE.md, onboarding brief, trace log]
  K[(KnowledgeGraph\nshared state)]
  O[Artifacts\n.cartography outputs]
  N[Navigator\nquery tools]
  U[User]

  A --> S
  A --> H
  S --> K
  H --> K
  K --> M
  M --> K
  K --> R
  R --> O
  O --> N
  N --> U
```

Pipeline rationale: Surveyor runs first to build a module graph and velocity map that seed all downstream reasoning. Hydrologist runs in parallel over the same repo to populate the lineage graph, which then enables blast-radius and source/sink queries. Semanticist depends on both graphs to generate purpose statements, clustering, and Day-One answers. Archivist runs last because it serializes the consolidated KnowledgeGraph into human-readable artifacts. The KnowledgeGraph is the central store that carries structured nodes/edges and annotations between all agents, and Navigator is layered on top of those artifacts for interactive querying. Tradeoffs: LLM calls are deferred to Semanticist after structural graphs exist to reduce token spend and prevent hallucinations from incomplete context. NetworkX is used for the KnowledgeGraph for simplicity and portability over a full graph database; this favors developer velocity and local runs at the cost of distributed scale and query performance on very large repos.

## 3) Accuracy Analysis Summary
1. Q1 Primary ingestion path: Partially correct (graphs built; ingestion path not explicitly derived)
2. Q2 Critical outputs: Partially correct (Cartographer artifacts reported; dbt-core outputs missing)
3. Q3 Blast radius: Partially correct (sources/sinks surfaced; critical-module blast radius missing)
4. Q4 Business logic concentration: Partially correct (PageRank highlights core modules; test fixtures skew signal)
5. Q5 Change velocity: Mostly correct (overlaps with manual top files; needs interpretation)

Why:
- LLM Day-One answers were not generated for dbt-core at the time of the run (Semanticist unavailable or skipped).
- Auto section is generic and not dbt-specific.
- PageRank is sensitive to test fixture density in dbt-core.

## 4) Limitations
Fixable gaps:
1. Jinja-heavy SQL reduces lineage accuracy (sqlglot fails on templates). A template-aware preprocessor or dbt compilation step could improve coverage.
2. Test fixtures can dominate PageRank without explicit de-prioritization. Adding test-path weighting or filters would correct centrality bias.
3. Day-One answers are LLM-dependent and can be absent if the model is unavailable. Add deterministic fallbacks or cached answers.

Fundamental constraints:
1. Dynamic Python data paths (table names constructed at runtime) are not reliably resolvable by static analysis.
2. Runtime-only behaviors (feature flags, environment-specific execution paths) can produce confident-looking but incomplete graphs.

Confidently wrong case:
- A dynamically constructed table name in a Python ETL could be reported as a literal placeholder, giving a false sense of lineage completeness.

## 5) FDE Applicability
Cold start: clone the repo, run `analyze`, then read `onboarding_brief.md` to orient on ingestion, outputs, and risk areas. During the engagement, use Navigator to answer daily questions (sources/sinks, blast radius, and implementation lookup) and keep a running list of verified file:line evidence for client conversations. Maintain `CODEBASE.md` by re-running analysis after significant changes so the context stays aligned with reality. The FDE still performs manual validation for dynamic runtime behavior, template-heavy SQL, and business-logic interpretation. Outputs feed directly into stakeholder updates and onboarding sessions: system map, lineage graph excerpts, and a short "what changed" briefing.

## 6) Self-Audit Results (Week 1 repo: Roo-Code)
Target: `.\_targets\Roo-Code`

Discrepancy #1:
- Description: Module graph is very small (13 nodes, 0 edges), and "Critical Path" is dominated by YAML config and SQL migration files.
- Explanation: The module graph only tracks a subset of file types, so the broader TS/JS codebase is under-represented and centrality skews toward configs and migrations.

Discrepancy #2:
- Description: "High-Velocity Files" are mostly repo meta/config files (changeset configs, git metadata) rather than core application modules.
- Explanation: Velocity is computed from git touches across the repo; without filtering, it can over-represent meta/config files that change frequently.

Discrepancy #3:
- Description: Roo-Code onboarding brief shows sources from SQL migrations but no sinks (out-degree 0 datasets list is empty).
- Explanation: The lineage graph is dominated by migration files that declare tables and constraints; it captures creation but not downstream consumption, so sinks are not inferred.

## Appendix: Evidence Files
- Manual analysis: `RECONNAISSANCE.md`
- System output: `.\_targets\dbt-core\.cartography\onboarding_brief.md`
- Module graph stats: `.\_targets\dbt-core\.cartography\module_graph.json`
- Lineage graph stats: `.\_targets\dbt-core\.cartography\lineage_graph.json`
