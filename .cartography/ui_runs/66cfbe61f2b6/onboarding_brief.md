# onboarding_brief.md

Generated: 2026-03-14T10:02:49Z
Target repo: C:\Users\user\Documents\brownfield-cartographer\brownfield-cartographer\_targets\Roo-Code

## Day-One Questions (Semanticist)

---

## Day-One Questions (Auto)

### 1) What does this system do?
- This repo was analyzed into a module graph (structure) and a lineage graph (data dependencies).

### 2) What are critical outputs?
- Outputs: `.cartography/module_graph.json`, `.cartography/lineage_graph.json`, `.cartography/CODEBASE.md`.

### 3) What are likely data sources/sinks?
- Sources (in-degree 0 datasets):
  - runs  [evidence: packages/evals/src/db/migrations/0001_add_timeout_to_runs.sql:1-1 (static), packages/evals/src/db/migrations/0001_lowly_captain_flint.sql:1-1 (static), packages/evals/src/db/migrations/0002_bouncy_blazing_skull.sql:1-1 (static), packages/evals/src/db/migrations/0003_simple_retro_girl.sql:1-1 (static)]
  - tasks_language_exercise_idx  [evidence: packages/evals/src/db/migrations/0004_sloppy_black_knight.sql:1-1 (static)]
  - public.runs  [evidence: packages/evals/src/db/migrations/0005_strong_skrulls.sql:1-1 (static)]
  - toolErrors_run_id_runs_id_fk  [evidence: packages/evals/src/db/migrations/0005_strong_skrulls.sql:1-1 (static)]
  - tasks_task_metrics_id_taskMetrics_id_fk  [evidence: packages/evals/src/db/migrations/0005_strong_skrulls.sql:1-1 (static)]
  - toolErrors  [evidence: packages/evals/src/db/migrations/0005_strong_skrulls.sql:1-1 (static)]
  - public.taskMetrics  [evidence: packages/evals/src/db/migrations/0005_strong_skrulls.sql:1-1 (static)]
  - toolErrors_task_id_tasks_id_fk  [evidence: packages/evals/src/db/migrations/0005_strong_skrulls.sql:1-1 (static)]
  - public.tasks  [evidence: packages/evals/src/db/migrations/0005_strong_skrulls.sql:1-1 (static)]
  - tasks_run_id_runs_id_fk  [evidence: packages/evals/src/db/migrations/0005_strong_skrulls.sql:1-1 (static)]
- Sinks (out-degree 0 datasets):

### 4) What are high-leverage modules?
- Top PageRank modules (structural centrality):
  - ellipsis.yaml (pagerank=0.076923)
  - pnpm-lock.yaml (pagerank=0.076923)
  - pnpm-workspace.yaml (pagerank=0.076923)
  - packages/evals/docker-compose.override.yml (pagerank=0.076923)
  - packages/evals/docker-compose.yml (pagerank=0.076923)
  - packages/evals/src/db/migrations/0000_young_trauma.sql (pagerank=0.076923)
  - packages/evals/src/db/migrations/0001_add_timeout_to_runs.sql (pagerank=0.076923)
  - packages/evals/src/db/migrations/0001_lowly_captain_flint.sql (pagerank=0.076923)
  - packages/evals/src/db/migrations/0002_bouncy_blazing_skull.sql (pagerank=0.076923)
  - packages/evals/src/db/migrations/0003_simple_retro_girl.sql (pagerank=0.076923)

### 5) What changed recently?
- Top changed files (30d):
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

