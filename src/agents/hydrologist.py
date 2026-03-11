import os
from pathlib import Path
import networkx as nx
from graph.knowledge_graph import KnowledgeGraph
from models.nodes import DatasetNode, TransformationNode

class Hydrologist:
    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg

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
                    data = ts_analyzer.analyze_python_module(str(file_path))
                    for op in data.get("data_ops", []):
                        # Future: refine to extract datasets being read/written in python
                        pass
                elif file.endswith('.sql'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            sql_query = f.read()
                        deps = sql_analyzer.extract_dependencies(sql_query)
                        
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
                                line_range="1",
                            )
                            self.kg.lineage_graph.add_node(rel_path, **t_node.dict())
                            
                            for s in sources:
                                self.kg.lineage_graph.add_edge(s, rel_path, type="consumes")
                            for t in targets:
                                self.kg.lineage_graph.add_edge(rel_path, t, type="produces")
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
                            if name not in self.kg.lineage_graph:
                                self.kg.lineage_graph.add_node(name, storage_type="table", owner="dbt")
                                
    def find_sources(self):
        return [n for n, d in self.kg.lineage_graph.in_degree() if d == 0]

    def find_sinks(self):
        return [n for n, d in self.kg.lineage_graph.out_degree() if d == 0]

    def blast_radius(self, node: str):
        if node not in self.kg.lineage_graph:
            return []
        return list(nx.descendants(self.kg.lineage_graph, node))
