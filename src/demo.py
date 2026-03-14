from __future__ import annotations

import json
import time
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import CartographyConfig
from graph.knowledge_graph import KnowledgeGraph
from agents.navigator import Navigator
from orchestrator import Orchestrator


@dataclass(frozen=True)
class DemoResult:
    repo_root: Path
    carto_dir: Path
    duration_s: float


def _parse_citation(c: str) -> Tuple[str, str]:
    """
    Parse "path:line-line (static)" or "path:line-line" -> (path, line_range).
    """
    s = (c or "").strip()
    if not s:
        return "", ""
    s = s.split(" (", 1)[0]
    if ":" not in s:
        return "", ""
    path, lr = s.rsplit(":", 1)
    return path.strip(), lr.strip()


def _read_lines(fp: Path, start: int, end: int) -> str:
    try:
        lines = fp.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return ""
    start = max(1, int(start))
    end = max(start, int(end))
    end = min(end, len(lines))
    chunk = lines[start - 1 : end]
    return "\n".join([f"{i+start:4d}: {ln}" for i, ln in enumerate(chunk)])


def _citation_snippet(repo_root: Path, cite: str) -> str:
    p, lr = _parse_citation(cite)
    if not p or not lr:
        return ""
    fp = (repo_root / p).resolve()
    if not fp.exists():
        return ""
    try:
        if "-" in lr:
            a, b = [int(x) for x in lr.split("-", 1)]
        else:
            a, b = int(lr), int(lr)
    except Exception:
        a, b = 1, 1
    return _read_lines(fp, a, min(b, a + 60))


def run_demo(
    *,
    repo_path: Path,
    config: CartographyConfig,
    output_dir: Optional[Path] = None,
    dataset: Optional[str] = None,
    module_path: Optional[str] = None,
    notes_path: Optional[Path] = None,
) -> DemoResult:
    """
    Scripted demo for the rubric steps:
    1) Cold start analysis (timed)
    2) Lineage query upstream traversal (with citations)
    3) Blast radius on module or dataset
    4) Show onboarding brief + verify 2 citations
    5) Living context injection instructions (manual comparison)
    6) Self-audit against ARCHITECTURE_NOTES.md (if present)
    """
    repo_root = repo_path.resolve()
    t0 = time.time()
    orch = Orchestrator()
    orch.run_analysis(repo_root, output_dir=output_dir, config=config, incremental=False)
    duration_s = time.time() - t0

    carto_dir = repo_root / ".cartography"
    print("\nSTEP 1: Cold Start")
    print(f"- Duration: {duration_s:.2f}s")
    print(f"- CODEBASE: {str((carto_dir / 'CODEBASE.md').as_posix())}")

    kg = KnowledgeGraph()
    kg.load_from_dir(carto_dir)
    nav = Navigator(kg, repo_root=repo_root, config=config, graph_dir=carto_dir)

    # Pick defaults if not provided.
    ds = dataset
    if not ds:
        sinks = nav.list_sinks(limit=10)
        ds = sinks[0] if sinks else ""
    mp = module_path
    if not mp:
        # pick top pagerank module if available
        scored = []
        for n, a in kg.module_graph.nodes(data=True):
            scored.append((float(a.get("pagerank") or 0.0), str(n)))
        scored.sort(reverse=True)
        mp = scored[0][1] if scored else ""

    print("\nSTEP 2: Lineage Query")
    if ds:
        res = nav.trace_lineage_tool(node=ds, direction="up", max_depth=8)
        print(f"- Query: What upstream sources feed {ds}?")
        paths = res.get("result") or []
        cites = res.get("citations") or []
        print(f"- Paths returned: {len(paths)}")
        print("- Sample paths:")
        for p in paths[:6]:
            if isinstance(p, list):
                print("  - " + " -> ".join([str(x) for x in p]))
        print("- Citations:")
        for c in cites[:12]:
            print(f"  - {c}")
    else:
        print("- (No dataset found in lineage graph; try analyzing a data repo.)")

    print("\nSTEP 3: Blast Radius")
    node = mp or ds
    if node:
        br = nav.blast_radius_tool(node)
        impacted = br.get("result") or []
        cites = br.get("citations") or []
        print(f"- Node: {node}")
        print(f"- Impacted count: {len(impacted)}")
        for it in impacted[:10]:
            p = it.get("path") if isinstance(it, dict) else None
            if isinstance(p, list):
                print("  - " + " -> ".join([str(x) for x in p]))
        if cites:
            print("- Citations:")
            for c in cites[:12]:
                print(f"  - {c}")
    else:
        print("- (No module/dataset available.)")

    print("\nSTEP 4: Day-One Brief Verification")
    ob = (carto_dir / "onboarding_brief.md").read_text(encoding="utf-8", errors="ignore")
    print(f"- Brief: {str((carto_dir / 'onboarding_brief.md').as_posix())}")
    # Find up to 2 citations in the brief, then print their snippets.
    citations: List[str] = []
    rx = re.compile(r"(?P<path>[A-Za-z0-9_./\\\\-]+):(?P<lr>\\d+(?:-\\d+)?)\\s*\\(static\\)")
    for line in ob.splitlines():
        for m in rx.finditer(line):
            citations.append(f"{m.group('path')}:{m.group('lr')} (static)")
        if len(citations) >= 2:
            break

    # Fallback: accept evidence blocks like "[evidence: a.py:1-2 (static), b.sql:10-20 (static)]"
    if len(citations) < 2:
        rx2 = re.compile(r"(?P<path>[A-Za-z0-9_./\\\\-]+):(?P<lr>\\d+(?:-\\d+)?)")
        for line in ob.splitlines():
            if "evidence:" not in line.lower():
                continue
            for m in rx2.finditer(line):
                citations.append(f"{m.group('path')}:{m.group('lr')}")
            if len(citations) >= 2:
                break

    # De-dupe while preserving order.
    seen = set()
    citations = [c for c in citations if not (c in seen or seen.add(c))]

    if citations:
        for c in citations[:2]:
            p, lr = _parse_citation(c)
            if not p:
                continue
            print(f"- Verify citation: {p}:{lr}")
            snip = _citation_snippet(repo_root, c)
            if snip:
                print(snip)
            else:
                print("  (could not load snippet)")
    else:
        print("- (No file:line citations found in onboarding_brief.md for this repo.)")

    print("\nUI TIP")
    print("- For an interactive graph map: run `src/cli.py serve` then open `/graph` and pick module/lineage.")

    print("\nSTEP 5: Living Context Injection (Manual)")
    print(f"- Inject: {str((carto_dir / 'CODEBASE.md').as_posix())}")
    print("- New AI session: set system prompt to contents of CODEBASE.md, then ask an architecture question.")
    print("- Example question: 'What are the entry points and critical path in this repo?'")
    print("- Compare: ask the same question in a fresh session without CODEBASE.md injected.")

    print("\nSTEP 6: Self-Audit (Optional)")
    default_notes = (repo_root / "ARCHITECTURE_NOTES.md").resolve()
    notes_fp = notes_path.resolve() if notes_path else default_notes
    if notes_fp.exists() and (carto_dir / "CODEBASE.md").exists():
        notes = notes_fp.read_text(encoding="utf-8", errors="ignore").splitlines()
        codebase_lines = (carto_dir / "CODEBASE.md").read_text(encoding="utf-8", errors="ignore").splitlines()

        def _first_nonmatching_line(a: List[str], b_joined: str) -> Tuple[int, str]:
            for idx, ln in enumerate(a, start=1):
                s = (ln or "").strip()
                if not s:
                    continue
                if len(s) < 8:
                    continue
                if s.startswith("#"):
                    continue
                if s not in b_joined:
                    return idx, s
            return 0, ""

        notes_joined = "\n".join(codebase_lines)
        codebase_joined = "\n".join(notes)

        n_line, n_text = _first_nonmatching_line(notes, notes_joined)
        c_line, c_text = _first_nonmatching_line(codebase_lines, codebase_joined)

        print(f"- Notes: {str(notes_fp.as_posix())}")
        print(f"- CODEBASE: {str((carto_dir / 'CODEBASE.md').as_posix())}")
        if n_line and n_text:
            print(f"- Discrepancy candidate (in notes, not in CODEBASE): {notes_fp.name}:{n_line}")
            print(f"  {n_text}")
        if c_line and c_text:
            print(f"- Discrepancy candidate (in CODEBASE, not in notes): CODEBASE.md:{c_line}")
            print(f"  {c_text}")
        if not ((n_line and n_text) or (c_line and c_text)):
            print("- No obvious textual discrepancy found (try adding more detailed notes or use a narrower repo).")
    else:
        if not notes_fp.exists():
            print(f"- Skipped: notes file not found at {str(notes_fp.as_posix())}")
            print("- Tip: pass `--notes path/to/ARCHITECTURE_NOTES.md` to `cli.py demo`.")
        else:
            print("- Skipped: CODEBASE.md not found (did analysis run successfully?)")

    return DemoResult(repo_root=repo_root, carto_dir=carto_dir, duration_s=duration_s)
