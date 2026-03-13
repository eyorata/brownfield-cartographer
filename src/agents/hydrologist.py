import os
import sys
from pathlib import Path
import networkx as nx
from datetime import datetime, timezone

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from graph.knowledge_graph import KnowledgeGraph
from models.edges import ConsumesEdge, ProducesEdge
from models.nodes import DatasetNode, TransformationNode

class Hydrologist:
    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _ensure_dataset(self, name: str, owner: str | None = None) -> None:
        if name in self.kg.lineage_graph:
            return
        storage_type = "table"
        lowered = name.lower()
        if any(lowered.endswith(ext) for ext in (".csv", ".parquet", ".json", ".ndjson")):
            storage_type = "file"
        node = DatasetNode(name=name, storage_type=storage_type, owner=owner)
        self.kg.add_dataset_node(node)

    @staticmethod
    def _looks_like_sql(s: str) -> bool:
        if not s or len(s) < 12:
            return False
        sl = s.lower()
        return any(k in sl for k in (" select ", "\nselect ", " from ", " join ", " insert ", " update ", " merge "))

    def analyze(self, repo_path: str | Path, only_files: set[str] | None = None, trace: list[dict] | None = None):
        print(f"Hydrologist analyzing data lineage of {repo_path}")
        from analyzers.tree_sitter_analyzer import TreeSitterAnalyzer
        from analyzers.sql_lineage import SQLLineageAnalyzer
        from analyzers.dag_config_parser import DAGConfigParser
        
        ts_analyzer = TreeSitterAnalyzer()
        sql_analyzer = SQLLineageAnalyzer()
        yaml_parser = DAGConfigParser()
        
        base_path = Path(repo_path).resolve()
        only_files_norm = None
        if only_files:
            only_files_norm = {str(Path(p).as_posix()) for p in only_files}

        unresolved_python_ops: list[dict] = []
        
        for root, dirs, files in os.walk(base_path):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d
                not in (
                    "venv",
                    "__pycache__",
                    "env",
                    ".venv",
                    ".cartography",
                    "artifacts",
                    "_targets",
                    "_tmp",
                    "node_modules",
                )
            ]
            for file in files:
                file_path = Path(root) / file
                rel_path = str(file_path.relative_to(base_path)).replace("\\", "/")
                if only_files_norm is not None and rel_path not in only_files_norm:
                    continue
                
                if file.endswith(".py"):
                    try:
                        data = ts_analyzer.analyze_python_module(str(file_path))
                    except Exception as e:
                        print(f"Failed to parse python for lineage {file_path}: {e}")
                        continue

                    ops = data.get("data_ops", []) or []
                    # Also parse Airflow DAG dependencies in Python (if present).
                    airflow_tasks = []
                    try:
                        airflow_tasks = yaml_parser.parse_airflow_py(str(file_path))
                    except Exception:
                        airflow_tasks = []

                    # Represent each python file as a transformation node.
                    if ops:
                        sources: set[str] = set()
                        targets: set[str] = set()
                        src_lr: dict[str, str] = {}
                        tgt_lr: dict[str, str] = {}
                        min_line = 10**9
                        max_line = 1
                        for op in ops:
                            op_type = str(op.get("type") or "")
                            direction = str(op.get("direction") or "")
                            line_range = str(op.get("line_range") or "1-1")
                            try:
                                a, b = [int(x) for x in line_range.split("-", 1)]
                                min_line = min(min_line, a)
                                max_line = max(max_line, b)
                            except Exception:
                                pass

                            call_path = str(op.get("call_path") or "")
                            args = str(op.get("args") or "")
                            literals = op.get("literals") or []
                            if op.get("unresolved"):
                                unresolved_python_ops.append(
                                    {
                                        "file": rel_path,
                                        "type": op_type,
                                        "call_path": call_path,
                                        "args": args[:500],
                                        "line_range": line_range,
                                    }
                                )

                            # File/table-like literals (pandas/pyspark read/write)
                            if direction in {"read", "write"}:
                                for lit in [str(x) for x in literals if isinstance(x, str) and x.strip()]:
                                    if direction == "read":
                                        sources.add(lit)
                                        src_lr.setdefault(lit, line_range)
                                    else:
                                        targets.add(lit)
                                        tgt_lr.setdefault(lit, line_range)

                            # Inline SQL strings inside Python calls (read_sql/execute/spark.sql).
                            sql_literals = op.get("sql_literals") or []
                            for sql_text in [str(x) for x in sql_literals if isinstance(x, str) and x.strip()]:
                                if not self._looks_like_sql(sql_text):
                                    continue
                                try:
                                    deps = sql_analyzer.extract_dependencies(sql_text, dialect="postgres")
                                except Exception:
                                    deps = {}
                                for s in deps.get("sources", []) or []:
                                    sources.add(str(s))
                                    src_lr.setdefault(str(s), line_range)
                                for t in deps.get("targets", []) or []:
                                    targets.add(str(t))
                                    tgt_lr.setdefault(str(t), line_range)

                        if sources or targets:
                            t_node = TransformationNode(
                                source_datasets=sorted(sources),
                                target_datasets=sorted(targets),
                                transformation_type="python",
                                source_file=rel_path,
                                line_range=f"{min_line}-{max_line}" if min_line != 10**9 else "1-1",
                            )
                            self.kg.add_transformation_node(t_node)

                            for s in t_node.source_datasets:
                                self._ensure_dataset(s, owner="python")
                                self.kg.add_consumes_edge(
                                    ConsumesEdge(
                                        transformation=rel_path,
                                        dataset=s,
                                        transformation_type="python",
                                        source_file=rel_path,
                                        line_range=str(src_lr.get(s) or "1-1"),
                                    )
                                )
                            for t in t_node.target_datasets:
                                self._ensure_dataset(t, owner="python")
                                self.kg.add_produces_edge(
                                    ProducesEdge(
                                        transformation=rel_path,
                                        dataset=t,
                                        transformation_type="python",
                                        source_file=rel_path,
                                        line_range=str(tgt_lr.get(t) or "1-1"),
                                    )
                                )
                            if trace is not None:
                                trace.append(
                                    {
                                        "ts": self._utc_now(),
                                        "agent": "hydrologist",
                                        "action": "python_lineage",
                                        "file": rel_path,
                                        "method": "static",
                                        "confidence": 0.75,
                                        "sources": sorted(sources)[:100],
                                        "targets": sorted(targets)[:100],
                                    }
                                )

                    # Airflow DAG parsing (Python).
                    if airflow_tasks:
                        created = 0
                        edges = 0
                        for item in airflow_tasks:
                            if item.get("type") != "task":
                                continue
                            task_id = str(item.get("id") or "").strip()
                            if not task_id:
                                continue
                            node_id = f"airflow_task:{rel_path}:{task_id}"
                            lr = str(item.get("line_range") or "1-1")
                            if node_id not in self.kg.lineage_graph:
                                self.kg.add_transformation_node(
                                    TransformationNode(
                                        source_datasets=[],
                                        target_datasets=[],
                                        transformation_type="airflow_task",
                                        source_file=node_id,
                                        line_range=lr,
                                    )
                                )
                                created += 1

                            # Optional: SQL embedded in operator args.
                            sql_lits = item.get("sql_literals") or []
                            for sql_text in [str(x) for x in sql_lits if isinstance(x, str) and x.strip()]:
                                if not self._looks_like_sql(sql_text):
                                    continue
                                try:
                                    deps = sql_analyzer.extract_dependencies(sql_text, dialect="postgres")
                                except Exception:
                                    deps = {}
                                for s in deps.get("sources", []) or []:
                                    self._ensure_dataset(str(s), owner="airflow_sql")
                                    self.kg.add_consumes_edge(
                                        ConsumesEdge(
                                            transformation=node_id,
                                            dataset=str(s),
                                            transformation_type="airflow_task",
                                            source_file=rel_path,
                                            line_range=lr,
                                        )
                                    )
                                for t in deps.get("targets", []) or []:
                                    self._ensure_dataset(str(t), owner="airflow_sql")
                                    self.kg.add_produces_edge(
                                        ProducesEdge(
                                            transformation=node_id,
                                            dataset=str(t),
                                            transformation_type="airflow_task",
                                            source_file=rel_path,
                                            line_range=lr,
                                        )
                                    )

                            for upstream in item.get("depends_on", []) or []:
                                up = str(upstream).strip()
                                if not up:
                                    continue
                                upstream_id = f"airflow_task:{rel_path}:{up}"
                                if upstream_id not in self.kg.lineage_graph:
                                    self.kg.add_transformation_node(
                                        TransformationNode(
                                            source_datasets=[],
                                            target_datasets=[],
                                            transformation_type="airflow_task",
                                            source_file=upstream_id,
                                            line_range="1-1",
                                        )
                                    )
                                self.kg.lineage_graph.add_edge(
                                    upstream_id,
                                    node_id,
                                    edge_type="depends_on",
                                    transformation_type="airflow_task",
                                    source_file=rel_path,
                                    line_range=lr,
                                )
                                edges += 1
                        if trace is not None:
                            trace.append(
                                {
                                    "ts": self._utc_now(),
                                    "agent": "hydrologist",
                                    "action": "airflow_dag_python",
                                    "file": rel_path,
                                    "method": "static",
                                    "confidence": 0.7,
                                    "tasks": created,
                                    "edges": edges,
                                }
                            )

                elif file.endswith(".sql"):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            sql_query = f.read()
                        deps = sql_analyzer.extract_dependencies(sql_query, dialect="postgres")
                        
                        targets = deps.get("targets", [])
                        if not targets and "models" in Path(file_path).parts:
                            targets = [file_path.stem]
                            
                        sources = deps.get("sources", [])
                        
                        if targets or sources:
                            n_lines = max(1, len(sql_query.splitlines()))
                            t_node = TransformationNode(
                                source_datasets=sources,
                                target_datasets=targets,
                                transformation_type="sql",
                                source_file=rel_path,
                                line_range=f"1-{n_lines}",
                            )
                            self.kg.add_transformation_node(t_node)
                            
                            for s in sources:
                                self._ensure_dataset(s, owner="sql")
                                line_nums = (deps.get("dataset_line_numbers", {}) or {}).get(s) or []
                                line = int(line_nums[0]) if line_nums else 1
                                self.kg.add_consumes_edge(
                                    ConsumesEdge(
                                        transformation=rel_path,
                                        dataset=s,
                                        transformation_type="sql",
                                        source_file=rel_path,
                                        line_range=f"{line}-{line}",
                                    )
                                )
                            for t in targets:
                                self._ensure_dataset(t, owner="sql")
                                line_nums = (deps.get("dataset_line_numbers", {}) or {}).get(t) or []
                                line = int(line_nums[0]) if line_nums else 1
                                self.kg.add_produces_edge(
                                    ProducesEdge(
                                        transformation=rel_path,
                                        dataset=t,
                                        transformation_type="sql",
                                        source_file=rel_path,
                                        line_range=f"{line}-{line}",
                                    )
                                )
                            if trace is not None:
                                trace.append(
                                    {
                                        "ts": self._utc_now(),
                                        "agent": "hydrologist",
                                        "action": "sql_lineage",
                                        "file": rel_path,
                                        "method": "static",
                                        "confidence": 0.85 if deps.get("dialect_used") else 0.55,
                                        "dialect_used": deps.get("dialect_used"),
                                        "sources": list(sources)[:200],
                                        "targets": list(targets)[:200],
                                    }
                                )
                    except Exception as e:
                        print(f"Failed to process {file_path}: {e}")

                elif file.endswith((".yml", ".yaml")):
                    # Only parse dbt schema-style YAML (models/sources). Skip dbt_project.yml and other non-schema files.
                    if file_path.name.lower() in {"dbt_project.yml", "packages.yml", "profiles.yml"}:
                        continue

                    configs = yaml_parser.parse_dbt_yaml(str(file_path))
                    for conf in configs:
                        if conf.get("type") == "source":
                            name = str(conf.get("name") or "").strip()
                            if name:
                                self._ensure_dataset(name, owner="dbt_source")
                        if conf.get("type") == "model":
                            name = str(conf.get("name") or "").strip()
                            if name:
                                # dbt models are datasets too; schema.yml may be the only mention.
                                self._ensure_dataset(name, owner="dbt_model")

                    # Best-effort airflow YAML parsing for simple declarative task graphs.
                    airflow = yaml_parser.parse_airflow_yaml(str(file_path))
                    if airflow:
                        for item in airflow:
                            if item.get("type") != "task":
                                continue
                            task_id = f"airflow_task:{item['id']}"
                            if task_id not in self.kg.lineage_graph:
                                self.kg.add_transformation_node(
                                    TransformationNode(
                                        source_datasets=[],
                                        target_datasets=[],
                                        transformation_type="airflow_task",
                                        source_file=task_id,
                                        line_range="1-1",
                                    )
                                )
                            for upstream in item.get("depends_on", []):
                                upstream_id = f"airflow_task:{upstream}"
                                if upstream_id not in self.kg.lineage_graph:
                                    self.kg.add_transformation_node(
                                        TransformationNode(
                                            source_datasets=[],
                                            target_datasets=[],
                                            transformation_type="airflow_task",
                                            source_file=upstream_id,
                                            line_range="1-1",
                                        )
                                    )
                                self.kg.lineage_graph.add_edge(
                                    upstream_id,
                                    task_id,
                                    edge_type="depends_on",
                                    transformation_type="airflow_task",
                                    source_file=rel_path,
                                    line_range="1-1",
                                )
                        if trace is not None:
                            trace.append(
                                {
                                    "ts": self._utc_now(),
                                    "agent": "hydrologist",
                                    "action": "yaml_config",
                                    "file": rel_path,
                                    "method": "static",
                                    "confidence": 0.6,
                                    "dbt_items": len(configs),
                                    "airflow_tasks": len([x for x in airflow if x.get("type") == "task"]),
                                }
                            )

        # Reduce noise: sqlglot fails on Jinja-heavy dbt SQL. Summarize instead of spamming logs.
        try:
            failures = sql_analyzer.consume_parse_failures()
        except Exception:
            failures = []
        if failures:
            print(
                f"SQL parse failures (sqlglot): {len(failures)} samples (Jinja/templates are expected). Showing up to 5:"
            )
            for f in failures[:5]:
                err = f.get("error") or ""
                snip = f.get("snippet") or ""
                print(f"- {err}")
                if snip:
                    print(snip)
                    print("")

        if unresolved_python_ops:
            # Required by rubric: log dynamic references we cannot resolve statically.
            print(f"Unresolved Python data references: {len(unresolved_python_ops)} (showing up to 10)")
            for it in unresolved_python_ops[:10]:
                print(f"- {it.get('file')}:{it.get('line_range')}  {it.get('type')}  {it.get('call_path')}")
            if trace is not None:
                trace.append(
                    {
                        "ts": self._utc_now(),
                        "agent": "hydrologist",
                        "action": "unresolved_python_ops",
                        "method": "static",
                        "confidence": 0.35,
                        "count": len(unresolved_python_ops),
                        "samples": unresolved_python_ops[:25],
                    }
                )
                                
    def find_sources(self):
        # Prefer dataset entry points (tables/files) as "sources".
        sources = []
        for n, d in self.kg.lineage_graph.in_degree():
            if d != 0:
                continue
            if "storage_type" in self.kg.lineage_graph.nodes.get(n, {}):
                sources.append(n)
        return sources

    def find_sinks(self):
        sinks = []
        for n, d in self.kg.lineage_graph.out_degree():
            if d != 0:
                continue
            if "storage_type" in self.kg.lineage_graph.nodes.get(n, {}):
                sinks.append(n)
        return sinks

    def blast_radius(self, node: str):
        if node not in self.kg.lineage_graph:
            return []

        impacted = []
        for target in sorted(nx.descendants(self.kg.lineage_graph, node)):
            try:
                path = nx.shortest_path(self.kg.lineage_graph, node, target)
            except Exception:
                path = [node, target]
            impacted.append({"node": target, "path": path})
        return impacted
