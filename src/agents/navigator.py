from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import networkx as nx

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from agents.hydrologist import Hydrologist
from graph.knowledge_graph import KnowledgeGraph


@dataclass(frozen=True)
class TracePath:
    path: List[str]


class Navigator:
    """
    Interactive query agent over the serialized KnowledgeGraph artifacts.

    This is intentionally lightweight: it avoids external dependencies and uses
    NetworkX traversals over the stored graphs.
    """

    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg
        self.hydrologist = Hydrologist(self.kg)

    @staticmethod
    def _shorten(s: str, n: int = 120) -> str:
        if len(s) <= n:
            return s
        return s[: n - 3] + "..."

    def stats(self) -> Dict[str, Any]:
        return {
            "module_nodes": self.kg.module_graph.number_of_nodes(),
            "module_edges": self.kg.module_graph.number_of_edges(),
            "lineage_nodes": self.kg.lineage_graph.number_of_nodes(),
            "lineage_edges": self.kg.lineage_graph.number_of_edges(),
        }

    def list_sources(self, limit: int = 50) -> List[str]:
        return self.hydrologist.find_sources()[:limit]

    def list_sinks(self, limit: int = 50) -> List[str]:
        return self.hydrologist.find_sinks()[:limit]

    def blast_radius(self, dataset_or_node: str, limit: int = 200) -> List[Dict[str, Any]]:
        """
        Returns a list of downstream nodes with at least one example path.
        """
        results = self.hydrologist.blast_radius(dataset_or_node)
        return results[:limit]

    def trace_lineage(
        self,
        node: str,
        direction: str = "down",
        max_depth: int = 6,
        max_paths: int = 25,
    ) -> List[TracePath]:
        g = self.kg.lineage_graph
        if direction not in {"down", "up"}:
            raise ValueError("direction must be 'down' or 'up'")
        if node not in g:
            return []

        if direction == "up":
            g = g.reverse(copy=False)

        # Enumerate simple paths to sinks within depth. We cap aggressively to keep this usable.
        paths: List[TracePath] = []
        frontier: List[Tuple[str, List[str]]] = [(node, [node])]

        while frontier and len(paths) < max_paths:
            cur, pth = frontier.pop(0)
            if len(pth) - 1 >= max_depth:
                paths.append(TracePath(path=pth))
                continue

            nbrs = list(g.successors(cur))
            if not nbrs:
                paths.append(TracePath(path=pth))
                continue

            for nb in nbrs[:50]:
                if nb in pth:
                    continue
                frontier.append((nb, pth + [str(nb)]))

        return paths

    def module_summary(self, module_path: str, limit_neighbors: int = 30) -> Dict[str, Any]:
        g = self.kg.module_graph
        if module_path not in g:
            return {"found": False, "module": module_path}

        attrs = dict(g.nodes[module_path])
        outgoing = list(g.successors(module_path))[:limit_neighbors]
        incoming = list(g.predecessors(module_path))[:limit_neighbors]

        def _edge_meta(a: str, b: str) -> Dict[str, Any]:
            md = dict(g.get_edge_data(a, b) or {})
            md.pop("weight", None)
            return md

        return {
            "found": True,
            "module": module_path,
            "attrs": attrs,
            "imports_out": [{"to": str(x), "edge": _edge_meta(module_path, x)} for x in outgoing],
            "imports_in": [{"from": str(x), "edge": _edge_meta(x, module_path)} for x in incoming],
        }

