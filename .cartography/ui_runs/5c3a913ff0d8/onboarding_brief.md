# onboarding_brief.md

Generated: 2026-03-12T20:47:15Z
Target repo: C:\Users\user\Documents\brownfield-cartographer\brownfield-cartographer\_targets\dbt-core

## Day-One Questions (Semanticist)

---

## Day-One Questions (Auto)

### 1) What does this system do?
- This repo was analyzed into a module graph (structure) and a lineage graph (data dependencies).

### 2) What are critical outputs?
- Outputs: `.cartography/module_graph.json`, `.cartography/lineage_graph.json`, `.cartography/CODEBASE.md`.

### 3) What are likely data sources/sinks?
- Sources (in-degree 0 datasets):
  - seed
  - seed_source.seed
  - my_source.my_table
- Sinks (out-degree 0 datasets):
  - my_second_dbt_model
  - b
  - b_root_package_in_ref
  - model
  - incremental
  - metricflow_time_spine
  - metricflow_time_spine_second
  - model_to_unit_test
  - model_with_lots_of_schema_configs
  - snapshot_source
  - inner

### 4) What are high-leverage modules?
- Top PageRank modules (structural centrality):
  - tests/unit/utils/__init__.py (pagerank=0.017867)
  - tests/functional/snapshots/fixtures.py (pagerank=0.010899)
  - tests/functional/defer_state/fixtures.py (pagerank=0.010035)
  - tests/functional/graph_selection/fixtures.py (pagerank=0.006816)
  - tests/functional/partial_parsing/fixtures.py (pagerank=0.006816)
  - core/dbt/graph/graph.py (pagerank=0.006705)
  - tests/functional/sources/fixtures.py (pagerank=0.006076)
  - core/dbt/config/renderer.py (pagerank=0.005895)
  - tests/functional/configs/fixtures.py (pagerank=0.005540)
  - tests/unit/config/__init__.py (pagerank=0.005284)

### 5) What changed recently?
- Top changed files (30d):
  - core/hatch.toml (touches=6)
  - tests/functional/semantic_models/test_semantic_model_v2_parsing.py (touches=6)
  - tests/functional/semantic_models/fixtures.py (touches=5)
  - core/dbt/compilation.py (touches=4)
  - core/dbt/jsonschemas/project/0.0.110.json (touches=4)
  - core/dbt/jsonschemas/resources/latest.json (touches=4)
  - .github/workflows/structured-logging-schema-check.yml (touches=4)
  - .github/workflows/main.yml (touches=4)
  - tests/functional/artifacts/expected_manifest.py (touches=3)
  - core/dbt/cli/params.py (touches=3)

