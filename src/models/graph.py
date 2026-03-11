from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    data: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    data: Dict[str, Any] = Field(default_factory=dict)


class NodeLinkGraph(BaseModel):
    directed: bool = True
    multigraph: bool = False
    graph: Dict[str, Any] = Field(default_factory=dict)
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)

    @classmethod
    def from_networkx(cls, data: Dict[str, Any]) -> "NodeLinkGraph":
        nodes = [GraphNode(id=str(n.get("id")), data={k: v for k, v in n.items() if k != "id"}) for n in data.get("nodes", [])]
        edges = [
            GraphEdge(
                source=str(e.get("source")),
                target=str(e.get("target")),
                data={k: v for k, v in e.items() if k not in ("source", "target")},
            )
            for e in data.get("edges", [])
        ]
        return cls(
            directed=bool(data.get("directed", True)),
            multigraph=bool(data.get("multigraph", False)),
            graph=dict(data.get("graph", {})),
            nodes=nodes,
            edges=edges,
        )

