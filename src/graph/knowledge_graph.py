import networkx as nx
import json
from pathlib import Path

class KnowledgeGraph:
    def __init__(self):
        self.module_graph = nx.DiGraph()
        self.lineage_graph = nx.DiGraph()

    def add_module(self, module_node):
        self.module_graph.add_node(module_node.path, **module_node.dict())

    def add_import(self, source, target, weight=1):
        self.module_graph.add_edge(source, target, weight=weight)

    def serialize_module_graph(self, output_path: str):
        data = nx.node_link_data(self.module_graph)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

    def serialize_lineage_graph(self, output_path: str):
        data = nx.node_link_data(self.lineage_graph)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
