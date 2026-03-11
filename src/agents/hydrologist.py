import os
from pathlib import Path
import networkx as nx
from graph.knowledge_graph import KnowledgeGraph
from models.edges import ConsumesEdge, ProducesEdge
from models.nodes import DatasetNode, TransformationNode

class Hydrologist:
    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg

    def _ensure_dataset(self, name: str, owner: str | None = None) -> None:
        if name in self.kg.lineage_graph:
            return
        storage_type = "table"
        lowered = name.lower()
        if any(lowered.endswith(ext) for ext in (".csv", ".parquet", ".json", ".ndjson")):
            storage_type = "file"
        node = DatasetNode(name=name, storage_type=storage_type, owner=owner)
        self.kg.add_dataset_node(node)

    def analyze(self, repo_path: str | Path):
        print(f"Hydrologist analyzing data lineage of {repo_path}")
        from analyzers.tree_sitter_analyzer import TreeSitterAnalyzer
        from analyzers.sql_lineage import SQLLineageAnalyzer
        from analyzers.dag_config_parser import DAGConfigParser
        
        ts_analyzer = TreeSitterAnalyzer()
        sql_analyzer = SQLLineageAnalyzer()
        yaml_parser = DAGConfigParser()
        
        base_path = Path(repo_path).resolve()
        
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
                    "_targets",
                    "_tmp",
                    "node_modules",
                )
            ]
            for file in files:
                file_path = Path(root) / file
                rel_path = str(file_path.relative_to(base_path)).replace("\\", "/")
                
                if file.endswith('.py'):
                    try:
                        data = ts_analyzer.analyze_python_module(str(file_path))
                    except Exception as e:
                        print(f"Failed to parse python for lineage {file_path}: {e}")
                        continue

                    ops = data.get("data_ops", []) or []
                    if not ops:
                        continue

                    # Represent each python file as a transformation node.
                    sources: list[str] = []
                    targets: list[str] = []
                    for op in ops:
                        op_type = str(op.get("type") or "")
                        literals = op.get("literals") or []
                        lit = literals[0] if literals else None
                        if not lit:
                            continue

                        if "read" in op_type:
                            sources.append(lit)
                        if "write" in op_type or "to_" in op_type:
                            targets.append(lit)

                    if not sources and not targets:
                        continue

                    t_node = TransformationNode(
                        source_datasets=sorted(set(sources)),
                        target_datasets=sorted(set(targets)),
                        transformation_type="python",
                        source_file=rel_path,
                        line_range="1-1",
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
                                line_range="1",
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
                                line_range="1",
                            )
                        )
                elif file.endswith('.sql'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            sql_query = f.read()
                        deps = sql_analyzer.extract_dependencies(sql_query, dialect="postgres")
                        
                        targets = deps.get("targets", [])
                        if not targets and "models" in Path(file_path).parts:
                            targets = [file_path.stem]
                            
                        sources = deps.get("sources", [])
                        
                        if targets or sources:
                            t_node = TransformationNode(
                                source_datasets=sources,
                                target_datasets=targets,
                                transformation_type="sql",
                                source_file=rel_path,
                                line_range="1-1",
                            )
                            self.kg.add_transformation_node(t_node)
                            
                            for s in sources:
                                self._ensure_dataset(s, owner="sql")
                                line_nums = (deps.get("ref_line_numbers", {}) or {}).get(s) or (deps.get("source_line_numbers", {}) or {}).get(s) or []
                                line = str(line_nums[0]) if line_nums else "1"
                                self.kg.add_consumes_edge(
                                    ConsumesEdge(
                                        transformation=rel_path,
                                        dataset=s,
                                        transformation_type="sql",
                                        source_file=rel_path,
                                        line_range=line,
                                    )
                                )
                            for t in targets:
                                self._ensure_dataset(t, owner="sql")
                                self.kg.add_produces_edge(
                                    ProducesEdge(
                                        transformation=rel_path,
                                        dataset=t,
                                        transformation_type="sql",
                                        source_file=rel_path,
                                        line_range="1",
                                    )
                                )
                    except Exception as e:
                        print(f"Failed to process {file_path}: {e}")
                            
                elif file.endswith(('.yml', '.yaml')):
                    # Only parse dbt schema-style YAML (models/sources). Skip dbt_project.yml and other non-schema files.
                    if file_path.name.lower() in {"dbt_project.yml", "packages.yml", "profiles.yml"}:
                        continue

                    configs = yaml_parser.parse_dbt_yaml(str(file_path))
                    for conf in configs:
                        if conf["type"] == "source":
                            name = conf["name"]
                            self._ensure_dataset(name, owner="dbt")

                    # Best-effort airflow YAML parsing for simple declarative task graphs.
                    airflow = yaml_parser.parse_airflow_yaml(str(file_path))
                    for item in airflow:
                        if item.get("type") != "task":
                            continue
                        task_id = f"airflow_task:{item['id']}"
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
                            self.kg.lineage_graph.add_edge(upstream_id, task_id, edge_type="depends_on", source_file=rel_path)
                                
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
