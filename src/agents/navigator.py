from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypedDict

import networkx as nx
from langgraph.graph import END, StateGraph

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from config import CartographyConfig
from agents.hydrologist import Hydrologist
from graph.knowledge_graph import KnowledgeGraph
from llm import ChatMessage, OpenAICompatClient
from graph.semantic_index import SemanticIndex


@dataclass(frozen=True)
class TracePath:
    path: List[str]


@dataclass(frozen=True)
class Citation:
    file: str
    line_range: str
    snippet: str = ""


class ToolResult(TypedDict):
    ok: bool
    result: Any
    citations: List[str]


class Navigator:
    """
    Navigator agent.

    Supports:
    - Deterministic graph queries (sources/sinks/trace/blast/module summary)
    - LangGraph loop where a local LLM selects tools and produces a final response
      (for the "Master Thinker" rubric).
    """

    def __init__(
        self,
        kg: KnowledgeGraph,
        repo_root: Path | None = None,
        config: CartographyConfig | None = None,
        graph_dir: Path | None = None,
    ):
        self.kg = kg
        self.repo_root = repo_root
        self.config = config or CartographyConfig()
        self.hydrologist = Hydrologist(self.kg)
        self._llm = OpenAICompatClient(
            base_url=self.config.llm.base_url,
            api_key=self.config.llm.api_key,
            timeout_s=self.config.llm.timeout_s,
        )
        self.semantic_index: SemanticIndex | None = None
        try:
            gd = graph_dir or (self.repo_root / ".cartography" if self.repo_root else None)
            if gd:
                self.semantic_index = SemanticIndex.load(Path(gd) / "semantic_index.json")
        except Exception:
            self.semantic_index = None

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
        return self.hydrologist.blast_radius(dataset_or_node)[:limit]

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

    # ---- Tools (rubric-required) ----

    def _read_file_snippet(self, rel_path: str, start: int = 1, end: int = 80) -> Citation | None:
        if self.repo_root is None:
            return None
        fp = (self.repo_root / rel_path).resolve()
        if not fp.exists():
            return None
        try:
            lines = fp.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            return None
        start = max(1, int(start))
        end = max(start, int(end))
        end = min(end, len(lines))
        chunk = lines[start - 1 : end]
        snippet = "\n".join([f"{i+start:4d}: {ln}" for i, ln in enumerate(chunk)])
        return Citation(file=rel_path, line_range=f"{start}-{end}", snippet=snippet)

    def find_implementation(self, query: str, limit: int = 25) -> ToolResult:
        q = (query or "").strip()
        if not q:
            return {"ok": False, "result": "query is empty", "citations": []}
        matches: List[Dict[str, Any]] = []

        # Prefer semantic index vector search when available (rubric expectation).
        if self.semantic_index is not None:
            try:
                vec_hits = self.semantic_index.search(
                    q,
                    top_k=limit,
                    client=self._llm if self.semantic_index.embedding_kind == "embedding" else None,
                )
            except Exception:
                vec_hits = []
            for hit in vec_hits:
                path = str(hit.get("module") or "")
                if path not in self.kg.module_graph:
                    continue
                a = dict(self.kg.module_graph.nodes[path])
                fn = [f.get("name") for f in (a.get("function_defs") or []) if isinstance(f, dict) and f.get("name")]
                cl = [c.get("name") for c in (a.get("class_defs") or []) if isinstance(c, dict) and c.get("name")]
                kind = str(hit.get("kind") or "module")
                symbol = str(hit.get("symbol") or "")
                lr = str(hit.get("line_range") or "1-1")
                matches.append(
                    {
                        "module": path,
                        "kind": kind,
                        "symbol": symbol,
                        "line_range": lr,
                        "score": float(hit.get("score") or 0.0),
                        "functions": fn[:12],
                        "classes": cl[:12],
                        "pagerank": float(a.get("pagerank") or 0.0),
                        "velocity_30d": int(a.get("change_velocity_30d") or 0),
                        "method": "vector",
                    }
                )
            matches.sort(key=lambda m: (m.get("score", 0.0), m.get("pagerank", 0.0), m.get("velocity_30d", 0)), reverse=True)
            matches = matches[:limit]

        # Fallback: substring search over paths + symbol names.
        if not matches:
            ql = q.lower()
            for node_id, attrs in self.kg.module_graph.nodes(data=True):
                path = str(node_id)
                a = dict(attrs)
                fn = [f.get("name") for f in (a.get("function_defs") or []) if isinstance(f, dict) and f.get("name")]
                cl = [c.get("name") for c in (a.get("class_defs") or []) if isinstance(c, dict) and c.get("name")]
                hay = " ".join([path] + [str(x) for x in fn + cl]).lower()
                if ql in hay:
                    matches.append(
                        {
                            "module": path,
                            "functions": fn[:12],
                            "classes": cl[:12],
                            "pagerank": float(a.get("pagerank") or 0.0),
                            "velocity_30d": int(a.get("change_velocity_30d") or 0),
                            "method": "substring",
                        }
                    )
            matches.sort(key=lambda m: (m.get("pagerank", 0.0), m.get("velocity_30d", 0)), reverse=True)
            matches = matches[:limit]

        citations: List[str] = []
        for m in matches[:10]:
            start = 1
            end = 60
            try:
                lr = str(m.get("line_range") or "")
                if lr and "-" in lr:
                    a, b = [int(x) for x in lr.split("-", 1)]
                    start = max(1, a)
                    end = max(start, min(b, start + 80))
            except Exception:
                start, end = 1, 60
            c = self._read_file_snippet(m["module"], start, end)
            if c:
                citations.append(f"{c.file}:{c.line_range} (static)")
        return {"ok": True, "result": matches, "citations": citations}

    def _edge_citations_for_path(self, path: List[str]) -> List[str]:
        cites: List[str] = []
        g = self.kg.lineage_graph
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            data = g.get_edge_data(u, v) or {}
            sf = str(data.get("source_file") or "")
            lr = str(data.get("line_range") or "")
            if sf and lr:
                cites.append(f"{sf}:{lr} (static)")
        out: List[str] = []
        seen = set()
        for c in cites:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    def trace_lineage_tool(self, node: str, direction: str = "up", max_depth: int = 6) -> ToolResult:
        paths = self.trace_lineage(node=node, direction=direction, max_depth=max_depth, max_paths=10)
        out = []
        citations: List[str] = []
        for tp in paths:
            out.append(tp.path)
            citations.extend(self._edge_citations_for_path(tp.path))
        return {"ok": True, "result": out, "citations": citations[:30]}

    def blast_radius_tool(self, node: str) -> ToolResult:
        impacted = self.hydrologist.blast_radius(node)[:100]
        citations: List[str] = []
        for it in impacted[:30]:
            p = it.get("path") or []
            if isinstance(p, list):
                citations.extend(self._edge_citations_for_path([str(x) for x in p]))
        return {"ok": True, "result": impacted, "citations": citations[:40]}

    def explain_module(self, module_path: str) -> ToolResult:
        info = self.module_summary(module_path)
        if not info.get("found"):
            return {"ok": False, "result": "module not found", "citations": []}
        attrs = info.get("attrs") or {}
        summary = {
            "module": module_path,
            "purpose_statement": attrs.get("purpose_statement"),
            "domain_cluster": attrs.get("domain_cluster"),
            "doc_drift_score": attrs.get("doc_drift_score"),
            "doc_drift_flags": attrs.get("doc_drift_flags"),
            "pagerank": attrs.get("pagerank"),
            "change_velocity_30d": attrs.get("change_velocity_30d"),
            "is_dead_code_candidate": attrs.get("is_dead_code_candidate"),
            "imports_out_count": len(info.get("imports_out") or []),
            "imports_in_count": len(info.get("imports_in") or []),
        }
        c = self._read_file_snippet(module_path, 1, 80)
        citations = [f"{c.file}:{c.line_range} (static)"] if c else []
        return {"ok": True, "result": summary, "citations": citations}

    # ---- LangGraph loop ----

    class _NavState(TypedDict):
        messages: List[Dict[str, str]]
        step: int
        pending_tool: Optional[Dict[str, Any]]
        final: Optional[str]
        citations: List[str]

    def _llm_node(self, state: "Navigator._NavState") -> "Navigator._NavState":
        max_steps = 6
        if state.get("step", 0) >= max_steps:
            state["final"] = "Reached max steps."
            return state

        sys_msg = (
            "You are a Navigator agent for a codebase knowledge graph. "
            "Decide the next tool call OR produce a final answer. "
            "Use citations provided by tools; do not fabricate file:line citations. "
            "Output strict JSON only.\n\n"
            "Tools:\n"
            "- find_implementation(query: string)\n"
            "- trace_lineage(node: string, direction: 'up'|'down', max_depth: int)\n"
            "- blast_radius(node: string)\n"
            "- explain_module(module_path: string)\n\n"
            "JSON schema:\n"
            "{type:'tool', name:'find_implementation'|'trace_lineage'|'blast_radius'|'explain_module', args:{...}}\n"
            "OR {type:'final', answer:string}\n"
        )

        msgs: List[ChatMessage] = [ChatMessage(role="system", content=sys_msg)]
        for m in state.get("messages", [])[-14:]:
            msgs.append(ChatMessage(role=m.get("role", "user"), content=m.get("content", "")))

        try:
            out = self._llm.chat_completions(
                model=self.config.llm.model,
                messages=msgs,
                temperature=self.config.llm.temperature,
                max_tokens=min(900, int(self.config.llm.max_tokens)),
                response_format={"type": "json_object"},
            )
            parsed = json.loads(out)
        except Exception as e:
            state["final"] = f"LLM unavailable: {e}"
            return state

        if isinstance(parsed, dict) and parsed.get("type") == "final":
            state["final"] = str(parsed.get("answer") or "").strip()
            return state

        if isinstance(parsed, dict) and parsed.get("type") == "tool":
            state["pending_tool"] = {"name": parsed.get("name"), "args": parsed.get("args") or {}}
            return state

        state["final"] = "Invalid LLM response."
        return state

    def _tool_node(self, state: "Navigator._NavState") -> "Navigator._NavState":
        call = state.get("pending_tool") or {}
        name = str(call.get("name") or "")
        args = call.get("args") or {}

        result: ToolResult
        try:
            if name == "find_implementation":
                result = self.find_implementation(str(args.get("query") or ""))
            elif name == "trace_lineage":
                result = self.trace_lineage_tool(
                    node=str(args.get("node") or ""),
                    direction=str(args.get("direction") or "up"),
                    max_depth=int(args.get("max_depth") or 6),
                )
            elif name == "blast_radius":
                result = self.blast_radius_tool(str(args.get("node") or ""))
            elif name == "explain_module":
                result = self.explain_module(str(args.get("module_path") or ""))
            else:
                result = {"ok": False, "result": f"Unknown tool: {name}", "citations": []}
        except Exception as e:
            result = {"ok": False, "result": str(e), "citations": []}

        obs = {"tool": name, "ok": result["ok"], "result": result["result"], "citations": result["citations"]}
        state.setdefault("messages", []).append({"role": "assistant", "content": json.dumps(obs)})
        try:
            state.setdefault("citations", []).extend([str(c) for c in (result.get("citations") or [])])
        except Exception:
            pass
        state["pending_tool"] = None
        state["step"] = int(state.get("step", 0)) + 1
        return state

    def ask(self, question: str) -> str:
        if not self.config.navigator.use_langgraph:
            return "LangGraph mode disabled in config.navigator.use_langgraph"

        g = StateGraph(self._NavState)
        g.add_node("llm", self._llm_node)
        g.add_node("tool", self._tool_node)
        g.set_entry_point("llm")

        def _route(state: Navigator._NavState) -> str:
            if state.get("final"):
                return END
            if state.get("pending_tool"):
                return "tool"
            return END

        g.add_conditional_edges("llm", _route, {"tool": "tool", END: END})
        g.add_edge("tool", "llm")
        app = g.compile()

        state: Navigator._NavState = {
            "messages": [{"role": "user", "content": question}],
            "step": 0,
            "pending_tool": None,
            "final": None,
            "citations": [],
        }
        out = app.invoke(state)
        ans = str(out.get("final") or "(no answer)")
        if self.config.navigator.citations:
            cites = [str(c) for c in (out.get("citations") or []) if str(c).strip()]
            # Deduplicate but preserve order
            seen = set()
            uniq: List[str] = []
            for c in cites:
                if c in seen:
                    continue
                seen.add(c)
                uniq.append(c)
            if uniq:
                ans = ans.rstrip() + "\n\nCitations:\n" + "\n".join([f"- {c}" for c in uniq[:30]])
        return ans
