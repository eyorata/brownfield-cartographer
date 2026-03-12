from __future__ import annotations

import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from graph.knowledge_graph import KnowledgeGraph


class Archivist:
    """
    Writes "living context" artifacts into `.cartography/`.
    """

    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _top_modules(self, n: int = 15) -> List[Dict[str, Any]]:
        scored = []
        for node_id, attrs in self.kg.module_graph.nodes(data=True):
            scored.append(
                {
                    "path": str(node_id),
                    "pagerank": float(attrs.get("pagerank") or 0.0),
                    "change_velocity_30d": int(attrs.get("change_velocity_30d") or 0),
                    "domain_cluster": attrs.get("domain_cluster"),
                    "is_dead_code_candidate": bool(attrs.get("is_dead_code_candidate") or False),
                }
            )
        scored.sort(key=lambda x: x["pagerank"], reverse=True)
        return scored[:n]

    def write_codebase_md(self, repo_root: Path, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)

        module_nodes = self.kg.module_graph.number_of_nodes()
        module_edges = self.kg.module_graph.number_of_edges()
        lineage_nodes = self.kg.lineage_graph.number_of_nodes()
        lineage_edges = self.kg.lineage_graph.number_of_edges()

        top_vel = self.kg.module_graph.graph.get("top_velocity_files_30d") or []
        top_modules = self._top_modules()

        lines: List[str] = []
        lines.append("# CODEBASE.md")
        lines.append("")
        lines.append(f"Generated: {self._utc_now()}")
        lines.append(f"Target repo: {repo_root}")
        lines.append("")
        lines.append("## Graph Summary")
        lines.append(f"- Module graph: nodes={module_nodes}, edges={module_edges}")
        lines.append(f"- Lineage graph: nodes={lineage_nodes}, edges={lineage_edges}")
        lines.append("")
        lines.append("## Top Modules (PageRank)")
        for m in top_modules:
            lines.append(
                f"- {m['path']} (pagerank={m['pagerank']:.6f}, velocity_30d={m['change_velocity_30d']}, dead={m['is_dead_code_candidate']})"
            )
        lines.append("")
        lines.append("## Top Changed Files (30d, git log)")
        for item in top_vel[:15]:
            lines.append(f"- {item.get('path')} (touches={item.get('touches')})")
        lines.append("")
        lines.append("## Artifacts")
        lines.append(f"- module graph: `{(out_dir / 'module_graph.json').as_posix()}`")
        lines.append(f"- lineage graph: `{(out_dir / 'lineage_graph.json').as_posix()}`")
        lines.append(f"- onboarding brief: `{(out_dir / 'onboarding_brief.md').as_posix()}`")
        lines.append("")

        (out_dir / "CODEBASE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def write_onboarding_brief(self, repo_root: Path, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)

        sources = []
        sinks = []
        try:
            from agents.hydrologist import Hydrologist

            hyd = Hydrologist(self.kg)
            sources = hyd.find_sources()
            sinks = hyd.find_sinks()
        except Exception:
            sources, sinks = [], []

        lines: List[str] = []
        lines.append("# onboarding_brief.md")
        lines.append("")
        lines.append(f"Generated: {self._utc_now()}")
        lines.append(f"Target repo: {repo_root}")
        lines.append("")

        day_one = self.kg.module_graph.graph.get("day_one_answers")
        if isinstance(day_one, dict) and day_one:
            lines.append("## Day-One Questions (Semanticist)")
            lines.append("")
            for key, title in [
                ("q1_primary_ingestion_path", "1) Primary ingestion path"),
                ("q2_critical_outputs", "2) Critical outputs"),
                ("q3_blast_radius", "3) Blast radius"),
                ("q4_business_logic", "4) Business logic concentration"),
                ("q5_change_velocity", "5) Recent change velocity"),
            ]:
                v = day_one.get(key)
                if isinstance(v, dict):
                    ans = str(v.get("answer") or "").strip()
                    cites = v.get("citations") if isinstance(v.get("citations"), list) else []
                    lines.append(f"### {title}")
                    lines.append(f"- {ans}" if ans else "- (no answer)")
                    if cites:
                        lines.append("- Citations:")
                        for c in cites[:10]:
                            lines.append(f"  - {c}")
                    lines.append("")
            lines.append("---")
            lines.append("")
        lines.append("## Day-One Questions (Auto)")
        lines.append("")
        lines.append("### 1) What does this system do?")
        lines.append("- This repo was analyzed into a module graph (structure) and a lineage graph (data dependencies).")
        lines.append("")
        lines.append("### 2) What are critical outputs?")
        lines.append("- Outputs: `.cartography/module_graph.json`, `.cartography/lineage_graph.json`, `.cartography/CODEBASE.md`.")
        lines.append("")
        lines.append("### 3) What are likely data sources/sinks?")
        lines.append("- Sources (in-degree 0 datasets):")
        for s in sources[:25]:
            lines.append(f"  - {s}")
        lines.append("- Sinks (out-degree 0 datasets):")
        for s in sinks[:25]:
            lines.append(f"  - {s}")
        lines.append("")
        lines.append("### 4) What are high-leverage modules?")
        lines.append("- Top PageRank modules (structural centrality):")
        for m in self._top_modules(10):
            lines.append(f"  - {m['path']} (pagerank={m['pagerank']:.6f})")
        lines.append("")
        lines.append("### 5) What changed recently?")
        lines.append("- Top changed files (30d):")
        for item in (self.kg.module_graph.graph.get("top_velocity_files_30d") or [])[:15]:
            lines.append(f"  - {item.get('path')} (touches={item.get('touches')})")
        lines.append("")

        (out_dir / "onboarding_brief.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def write_trace(self, out_dir: Path, events: List[Dict[str, Any]]) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        trace_path = out_dir / "cartography_trace.jsonl"
        with trace_path.open("w", encoding="utf-8") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")
