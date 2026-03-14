# CODEBASE.md

Generated: 2026-03-14T10:02:49Z
Target repo: C:\Users\user\Documents\brownfield-cartographer\brownfield-cartographer\_targets\Roo-Code

## Architecture Overview
- Module graph: nodes=13, edges=0
- Lineage graph: nodes=18, edges=17
- LLM usage: used_tokens=0 / max_total_tokens=200000

## Critical Path
- High-centrality modules (PageRank):
  - ellipsis.yaml (pagerank=0.076923, velocity_30d=1, dead=False)
  - pnpm-lock.yaml (pagerank=0.076923, velocity_30d=1, dead=False)
  - pnpm-workspace.yaml (pagerank=0.076923, velocity_30d=1, dead=False)
  - packages/evals/docker-compose.override.yml (pagerank=0.076923, velocity_30d=1, dead=False)
  - packages/evals/docker-compose.yml (pagerank=0.076923, velocity_30d=1, dead=False)
  - packages/evals/src/db/migrations/0000_young_trauma.sql (pagerank=0.076923, velocity_30d=1, dead=False)
  - packages/evals/src/db/migrations/0001_add_timeout_to_runs.sql (pagerank=0.076923, velocity_30d=1, dead=False)
  - packages/evals/src/db/migrations/0001_lowly_captain_flint.sql (pagerank=0.076923, velocity_30d=1, dead=False)
  - packages/evals/src/db/migrations/0002_bouncy_blazing_skull.sql (pagerank=0.076923, velocity_30d=1, dead=False)
  - packages/evals/src/db/migrations/0003_simple_retro_girl.sql (pagerank=0.076923, velocity_30d=1, dead=False)
  - packages/evals/src/db/migrations/0004_sloppy_black_knight.sql (pagerank=0.076923, velocity_30d=1, dead=False)
  - packages/evals/src/db/migrations/0005_strong_skrulls.sql (pagerank=0.076923, velocity_30d=1, dead=False)
  - packages/evals/src/db/migrations/0006_worried_spectrum.sql (pagerank=0.076923, velocity_30d=1, dead=False)

## Data Sources & Sinks
- Sources (in-degree 0 datasets):
  - runs
  - tasks_language_exercise_idx
  - public.runs
  - toolErrors_run_id_runs_id_fk
  - tasks_task_metrics_id_taskMetrics_id_fk
  - toolErrors
  - public.taskMetrics
  - toolErrors_task_id_tasks_id_fk
  - public.tasks
  - tasks_run_id_runs_id_fk
- Sinks (out-degree 0 datasets):

## Known Debt
- Dead code candidates (heuristic: exported symbols with no importers):

## High-Velocity Files
- .changeset/README.md (touches=1)
- .changeset/changelog-config.js (touches=1)
- .changeset/config.json (touches=1)
- .dockerignore (touches=1)
- .env.sample (touches=1)
- .git-blame-ignore-revs (touches=1)
- .gitattributes (touches=1)
- .gitconfig (touches=1)
- .github/CODEOWNERS (touches=1)
- .github/ISSUE_TEMPLATE/bug_report.yml (touches=1)

## Module Purpose Index
- pnpm-workspace.yaml [table-null]: pnpm-workspace.yaml is a YAML configuration file.
- pnpm-lock.yaml [version-specifier]: pnpm-lock.yaml is a YAML configuration file.
- packages/evals/src/db/migrations/0006_worried_spectrum.sql [packages-evals]: packages/evals/src/db/migrations/0006_worried_spectrum.sql is a SQL file.
- packages/evals/src/db/migrations/0005_strong_skrulls.sql [table-null]: packages/evals/src/db/migrations/0005_strong_skrulls.sql is a SQL file.
- packages/evals/src/db/migrations/0004_sloppy_black_knight.sql [table-null]: packages/evals/src/db/migrations/0004_sloppy_black_knight.sql is a SQL file.
- packages/evals/src/db/migrations/0003_simple_retro_girl.sql [packages-evals]: packages/evals/src/db/migrations/0003_simple_retro_girl.sql is a SQL file.
- packages/evals/src/db/migrations/0002_bouncy_blazing_skull.sql [table-null]: packages/evals/src/db/migrations/0002_bouncy_blazing_skull.sql is a SQL file.
- packages/evals/src/db/migrations/0001_lowly_captain_flint.sql [table-null]: packages/evals/src/db/migrations/0001_lowly_captain_flint.sql is a SQL file.
- packages/evals/src/db/migrations/0001_add_timeout_to_runs.sql [table-null]: packages/evals/src/db/migrations/0001_add_timeout_to_runs.sql is a SQL file.
- packages/evals/src/db/migrations/0000_young_trauma.sql [table-null]: packages/evals/src/db/migrations/0000_young_trauma.sql is a SQL file.
- packages/evals/docker-compose.yml [version-specifier]: packages/evals/docker-compose.yml is a YAML configuration file.
- packages/evals/docker-compose.override.yml [version-specifier]: packages/evals/docker-compose.override.yml is a YAML configuration file.
- ellipsis.yaml [version-specifier]: ellipsis.yaml is a YAML configuration file.

## Artifacts
- module graph: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/ui_runs/66cfbe61f2b6/module_graph.json`
- lineage graph: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/ui_runs/66cfbe61f2b6/lineage_graph.json`
- semantic index: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/ui_runs/66cfbe61f2b6/semantic_index.json`
- onboarding brief: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/ui_runs/66cfbe61f2b6/onboarding_brief.md`
- trace: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/ui_runs/66cfbe61f2b6/cartography_trace.jsonl`

