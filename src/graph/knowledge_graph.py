from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Any

import networkx as nx

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from models.edges import CallsEdge, ConfiguresEdge, ConsumesEdge, ImportsEdge, ProducesEdge
from models.nodes import DatasetNode, ModuleNode, TransformationNode

class KnowledgeGraph:
    def __init__(self):
        self.module_graph = nx.DiGraph()
        self.lineage_graph = nx.DiGraph()

    # Typed, schema-aligned helpers. Agents can still manipulate the NetworkX
    # graphs directly, but these methods provide a consistent contract.

    def add_module_node(self, node: ModuleNode) -> None:
        self.module_graph.add_node(node.path, **node.model_dump(exclude_none=True))

    def add_import_edge(self, edge: ImportsEdge) -> None:
        self.module_graph.add_edge(
            edge.source_module,
            edge.target_module,
            weight=edge.weight,
            edge_type=edge.edge_type,
            source_file=edge.source_file,
            line_range=edge.line_range,
        )

    def add_dataset_node(self, node: DatasetNode) -> None:
        self.lineage_graph.add_node(node.name, **node.model_dump(exclude_none=True))

    def add_transformation_node(self, node: TransformationNode) -> None:
        # Use source_file as the transformation ID to keep it stable and traceable.
        self.lineage_graph.add_node(node.source_file, **node.model_dump(exclude_none=True))

    def add_consumes_edge(self, edge: ConsumesEdge, **attrs: Any) -> None:
        self.lineage_graph.add_edge(
            edge.dataset,
            edge.transformation,
            edge_type=edge.edge_type,
            transformation_type=edge.transformation_type,
            source_file=edge.source_file,
            line_range=edge.line_range,
            **attrs,
        )

    def add_produces_edge(self, edge: ProducesEdge, **attrs: Any) -> None:
        self.lineage_graph.add_edge(
            edge.transformation,
            edge.dataset,
            edge_type=edge.edge_type,
            transformation_type=edge.transformation_type,
            source_file=edge.source_file,
            line_range=edge.line_range,
            **attrs,
        )

    def add_calls_edge(self, edge: CallsEdge, **attrs: Any) -> None:
        self.module_graph.add_edge(
            edge.source_function,
            edge.target_function,
            edge_type=edge.edge_type,
            source_file=edge.source_file,
            line_range=edge.line_range,
            **attrs,
        )

    def add_configures_edge(self, edge: ConfiguresEdge, **attrs: Any) -> None:
        self.module_graph.add_edge(
            edge.config_file,
            edge.target,
            edge_type=edge.edge_type,
            source_file=edge.source_file,
            line_range=edge.line_range,
            **attrs,
        )

    def serialize_module_graph(self, output_path: str):
        data = nx.node_link_data(self.module_graph)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def serialize_lineage_graph(self, output_path: str):
        data = nx.node_link_data(self.lineage_graph)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def deserialize_module_graph(input_path: str | Path) -> nx.DiGraph:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return nx.node_link_graph(data, directed=True, multigraph=False)

    @staticmethod
    def deserialize_lineage_graph(input_path: str | Path) -> nx.DiGraph:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return nx.node_link_graph(data, directed=True, multigraph=False)

    def load_from_dir(self, output_dir: str | Path) -> None:
        output_dir = Path(output_dir)
        mg = output_dir / "module_graph.json"
        lg = output_dir / "lineage_graph.json"
        if mg.exists():
            self.module_graph = self.deserialize_module_graph(mg)
        if lg.exists():
            self.lineage_graph = self.deserialize_lineage_graph(lg)

    def prune_changed_files(self, changed_rel_paths: set[str]) -> None:
        """
        Incremental helper: remove nodes/edges that were produced from a set of source files.

        For module graph:
        - Node IDs are file paths. Remove nodes whose ID is in changed_rel_paths.
        - Remove edges whose 'source_file' is in changed_rel_paths.

        For lineage graph:
        - Transformation node IDs are source_file paths (sql/yaml/py). Remove those nodes.
        - Remove edges whose 'source_file' is in changed_rel_paths.

        Dataset nodes are not removed (they may be shared across transformations).
        """
        if not changed_rel_paths:
            return

        # Module graph prune
        for n in list(self.module_graph.nodes):
            if str(n) in changed_rel_paths:
                try:
                    self.module_graph.remove_node(n)
                except Exception:
                    pass
        for u, v, data in list(self.module_graph.edges(data=True)):
            if str(data.get("source_file") or "") in changed_rel_paths:
                try:
                    self.module_graph.remove_edge(u, v)
                except Exception:
                    pass

        # Lineage graph prune
        for n, data in list(self.lineage_graph.nodes(data=True)):
            # Transformation nodes are keyed by source file path.
            if str(n) in changed_rel_paths:
                try:
                    self.lineage_graph.remove_node(n)
                except Exception:
                    pass
        for u, v, data in list(self.lineage_graph.edges(data=True)):
            if str(data.get("source_file") or "") in changed_rel_paths:
                try:
                    self.lineage_graph.remove_edge(u, v)
                except Exception:
                    pass
