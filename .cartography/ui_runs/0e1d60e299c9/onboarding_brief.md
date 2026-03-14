# onboarding_brief.md

Generated: 2026-03-14T13:27:33Z
Target repo: C:\Users\user\Documents\brownfield-cartographer\brownfield-cartographer\_targets\Roo-Code

## Day-One Questions (Semanticist)

---

## Day-One Questions (Auto)

### 1) What is the primary data ingestion path?
- This repo was analyzed into a module graph (structure) and a lineage graph (data dependencies); explicit ingestion paths require manual confirmation or LLM synthesis.

### 2) What are the 3-5 most critical output datasets/endpoints?
- Outputs: `.cartography/module_graph.json`, `.cartography/lineage_graph.json`, `.cartography/CODEBASE.md`.

### 3) What is the blast radius if the most critical module fails?
- Sources (in-degree 0 datasets) can be used to trace downstream impact:
  - runs  [evidence: packages/evals/src/db/migrations/0001_add_timeout_to_runs.sql:1-1 (static), packages/evals/src/db/migrations/0001_lowly_captain_flint.sql:1-1 (static), packages/evals/src/db/migrations/0002_bouncy_blazing_skull.sql:1-1 (static), packages/evals/src/db/migrations/0003_simple_retro_girl.sql:1-1 (static)]
  - tasks_language_exercise_idx  [evidence: packages/evals/src/db/migrations/0004_sloppy_black_knight.sql:1-1 (static)]
  - tasks_task_metrics_id_taskMetrics_id_fk  [evidence: packages/evals/src/db/migrations/0005_strong_skrulls.sql:1-1 (static)]
  - public.taskMetrics  [evidence: packages/evals/src/db/migrations/0005_strong_skrulls.sql:1-1 (static)]
  - toolErrors_run_id_runs_id_fk  [evidence: packages/evals/src/db/migrations/0005_strong_skrulls.sql:1-1 (static)]
  - tasks_run_id_runs_id_fk  [evidence: packages/evals/src/db/migrations/0005_strong_skrulls.sql:1-1 (static)]
  - toolErrors  [evidence: packages/evals/src/db/migrations/0005_strong_skrulls.sql:1-1 (static)]
  - public.runs  [evidence: packages/evals/src/db/migrations/0005_strong_skrulls.sql:1-1 (static)]
  - public.tasks  [evidence: packages/evals/src/db/migrations/0005_strong_skrulls.sql:1-1 (static)]
  - toolErrors_task_id_tasks_id_fk  [evidence: packages/evals/src/db/migrations/0005_strong_skrulls.sql:1-1 (static)]
- Sinks (out-degree 0 datasets) indicate likely downstream impact:

### 4) Where is the business logic concentrated vs. distributed?
- Top PageRank modules (structural centrality) approximate concentration:
  - packages/types/src/providers/../model.ts (pagerank=0.009036)
  - webview-ui/src/components/settings/providers/../transforms.ts (pagerank=0.006606)
  - apps/cli/src/ui/components/../theme.ts (pagerank=0.003201)
  - apps/cli/src/agent/agent-state.ts (pagerank=0.002878)
  - packages/vscode-shim/src/classes/../types.ts (pagerank=0.002832)
  - webview-ui/src/components/settings/SettingsView.tsx (pagerank=0.002663)
  - src/api/providers/../../shared/api.ts (pagerank=0.002596)
  - src/core/tools/../../shared/tools.ts (pagerank=0.002538)
  - webview-ui/src/components/settings/providers/../ModelPicker.tsx (pagerank=0.002386)
  - packages/types/src/provider-settings.ts (pagerank=0.002365)

### 5) What has changed most frequently in the last 90 days (git velocity map)?
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

