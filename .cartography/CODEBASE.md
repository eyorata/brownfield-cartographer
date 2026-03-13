# CODEBASE.md

Generated: 2026-03-13T20:00:02Z
Target repo: C:\Users\user\Documents\brownfield-cartographer\brownfield-cartographer

## Architecture Overview
- Module graph: nodes=26, edges=1
- Lineage graph: nodes=0, edges=0
- LLM usage: used_tokens=0 / max_total_tokens=200000

## Critical Path
- High-centrality modules (PageRank):
  - src/llm/openai_compat.py (pagerank=0.068901, velocity_30d=2, dead=False)
  - cartography_config.yaml (pagerank=0.037244, velocity_30d=1, dead=False)
  - main.py (pagerank=0.037244, velocity_30d=1, dead=False)
  - src/cli.py (pagerank=0.037244, velocity_30d=10, dead=False)
  - src/config.py (pagerank=0.037244, velocity_30d=1, dead=True)
  - src/orchestrator.py (pagerank=0.037244, velocity_30d=10, dead=True)
  - src/ui_server.py (pagerank=0.037244, velocity_30d=4, dead=True)
  - src/__init__.py (pagerank=0.037244, velocity_30d=1, dead=False)
  - src/agents/archivist.py (pagerank=0.037244, velocity_30d=2, dead=True)
  - src/agents/hydrologist.py (pagerank=0.037244, velocity_30d=7, dead=True)
  - src/agents/navigator.py (pagerank=0.037244, velocity_30d=2, dead=True)
  - src/agents/semanticist.py (pagerank=0.037244, velocity_30d=4, dead=True)
  - src/agents/surveyor.py (pagerank=0.037244, velocity_30d=7, dead=True)
  - src/agents/__init__.py (pagerank=0.037244, velocity_30d=1, dead=False)
  - src/analyzers/dag_config_parser.py (pagerank=0.037244, velocity_30d=4, dead=True)

## Data Sources & Sinks
- Sources (in-degree 0 datasets):
- Sinks (out-degree 0 datasets):

## Known Debt
- Dead code candidates (heuristic: exported symbols with no importers):
  - src/config.py
  - src/orchestrator.py
  - src/ui_server.py
  - src/agents/archivist.py
  - src/agents/hydrologist.py
  - src/agents/navigator.py
  - src/agents/semanticist.py
  - src/agents/surveyor.py
  - src/analyzers/dag_config_parser.py
  - src/analyzers/sql_lineage.py
  - src/analyzers/tree_sitter_analyzer.py
  - src/graph/knowledge_graph.py
  - src/graph/semantic_index.py
  - src/models/edges.py
  - src/models/graph.py
  - src/models/nodes.py
- Potential documentation drift (heuristic/LLM):
  - src/ui_server.py (doc_drift_score=0.60, flags=no_docstring)
  - src/orchestrator.py (doc_drift_score=0.60, flags=no_docstring)
  - src/models/nodes.py (doc_drift_score=0.60, flags=no_docstring)
  - src/models/graph.py (doc_drift_score=0.60, flags=no_docstring)
  - src/models/edges.py (doc_drift_score=0.60, flags=no_docstring)
  - src/llm/openai_compat.py (doc_drift_score=0.60, flags=no_docstring)
  - src/graph/semantic_index.py (doc_drift_score=0.60, flags=no_docstring)
  - src/graph/knowledge_graph.py (doc_drift_score=0.60, flags=no_docstring)
  - src/config.py (doc_drift_score=0.60, flags=no_docstring)
  - src/cli.py (doc_drift_score=0.60, flags=no_docstring)
  - src/analyzers/tree_sitter_analyzer.py (doc_drift_score=0.60, flags=no_docstring)
  - src/analyzers/sql_lineage.py (doc_drift_score=0.60, flags=no_docstring)
  - src/analyzers/dag_config_parser.py (doc_drift_score=0.60, flags=no_docstring)
  - src/agents/surveyor.py (doc_drift_score=0.60, flags=no_docstring)
  - src/agents/semanticist.py (doc_drift_score=0.60, flags=no_docstring)

## High-Velocity Files
- src/cli.py (touches=10)
- src/orchestrator.py (touches=10)
- src/agents/hydrologist.py (touches=7)
- src/agents/surveyor.py (touches=7)
- src/analyzers/sql_lineage.py (touches=6)
- .gitignore (touches=5)
- src/ui_server.py (touches=4)
- src/agents/semanticist.py (touches=4)
- src/graph/knowledge_graph.py (touches=4)
- src/analyzers/dag_config_parser.py (touches=4)

## Module Purpose Index
- src/llm/openai_compat.py [models-graph]: src/llm/openai_compat.py defines classes: ChatMessage, OpenAICompatClient; functions: __init__, chat_completions, embeddings, get_models, is_available.
- src/ui_server.py [agents-analyzers]: src/ui_server.py defines classes: Handler, _JobStore; functions: __init__, create, do_GET, do_POST, get, log_message, score, serve.
- src/orchestrator.py [agents-analyzers]: src/orchestrator.py defines classes: Orchestrator; functions: __init__, run_analysis.
- src/models/nodes.py [models-graph]: src/models/nodes.py defines classes: DatasetNode, FunctionNode, ModuleNode, TransformationNode.
- src/models/graph.py [agents-analyzers]: src/models/graph.py defines classes: GraphEdge, GraphNode, NodeLinkGraph; functions: from_networkx.
- src/models/edges.py [models-graph]: src/models/edges.py defines classes: CallsEdge, ConfiguresEdge, ConsumesEdge, ImportsEdge, ProducesEdge.
- src/models/__init__.py [agents-analyzers]: src/models/__init__.py is a Python module.
- src/llm/__init__.py [agents-analyzers]: src/llm/__init__.py is a Python module.
- src/graph/semantic_index.py [agents-analyzers]: src/graph/semantic_index.py defines classes: SemanticIndex, SemanticIndexEntry; functions: __init__, build, embed_texts, from_json, load, save, search, to_json.
- src/graph/knowledge_graph.py [models-graph]: src/graph/knowledge_graph.py defines classes: KnowledgeGraph; functions: __init__, add_calls_edge, add_configures_edge, add_consumes_edge, add_dataset_node, add_import_edge, add_module_node, add_produces_edge.
- src/graph/__init__.py [agents-analyzers]: src/graph/__init__.py is a Python module.
- src/config.py [agents-analyzers]: src/config.py defines classes: CartographyConfig, IncrementalConfig, LLMConfig, NavigatorConfig, SemanticistConfig; functions: load_config.
- src/cli.py [agents-analyzers]: src/cli.py defines functions: main.
- src/analyzers/tree_sitter_analyzer.py [agents-analyzers]: src/analyzers/tree_sitter_analyzer.py defines classes: LanguageRouter, TreeSitterAnalyzer; functions: __init__, analyze_python_module, get_language, parse_python, parse_sql, parse_yaml, text, traverse.
- src/analyzers/sql_lineage.py [agents-analyzers]: src/analyzers/sql_lineage.py defines classes: SQLLineageAnalyzer; functions: __init__, consume_parse_failures, extract_dependencies.
- src/analyzers/dag_config_parser.py [agents-analyzers]: src/analyzers/dag_config_parser.py defines classes: DAGConfigParser; functions: parse_airflow_yaml, parse_dbt_yaml.
- src/analyzers/__init__.py [agents-analyzers]: src/analyzers/__init__.py is a Python module.
- src/agents/surveyor.py [agents-analyzers]: src/agents/surveyor.py defines classes: Surveyor; functions: __init__, analyze, resolve_module.
- src/agents/semanticist.py [agents-analyzers]: src/agents/semanticist.py defines classes: Citation, ContextWindowBudget, LLMBudget, PurposeResult, Semanticist; functions: __init__, annotate_modules, answer_day_one_questions, choose_model, remaining, render, run, spend.
- src/agents/navigator.py [agents-analyzers]: src/agents/navigator.py defines classes: Citation, Navigator, ToolResult, TracePath, _NavState; functions: __init__, ask, blast_radius, blast_radius_tool, explain_module, find_implementation, list_sinks, list_sources.
- src/agents/hydrologist.py [agents-analyzers]: src/agents/hydrologist.py defines classes: Hydrologist; functions: __init__, analyze, blast_radius, find_sinks, find_sources.
- src/agents/archivist.py [agents-analyzers]: src/agents/archivist.py defines classes: Archivist; functions: __init__, write_codebase_md, write_onboarding_brief, write_trace.
- src/agents/__init__.py [agents-analyzers]: src/agents/__init__.py is a Python module.
- src/__init__.py [agents-analyzers]: src/__init__.py is a Python module.
- main.py [models-graph]: main.py defines functions: main.
- cartography_config.yaml [cartography_config]: cartography_config.yaml is a YAML configuration file.

## Artifacts
- module graph: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/module_graph.json`
- lineage graph: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/lineage_graph.json`
- semantic index: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/semantic_index.json`
- onboarding brief: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/onboarding_brief.md`
- trace: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/cartography_trace.jsonl`

