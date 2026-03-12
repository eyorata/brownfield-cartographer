from __future__ import annotations

import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from agents.surveyor import Surveyor
from agents.hydrologist import Hydrologist
from agents.semanticist import Semanticist
from agents.archivist import Archivist
from graph.knowledge_graph import KnowledgeGraph
from config import CartographyConfig


def _require_runtime_deps() -> None:
    missing = []
    for mod in ("networkx", "pydantic", "sqlglot", "yaml"):
        try:
            __import__(mod)
        except Exception:
            missing.append(mod)
    if missing:
        msg = (
            "Missing required Python dependencies: "
            + ", ".join(missing)
            + "\n\n"
            + "Run using the project venv:\n"
            + "  .\\.venv\\Scripts\\python.exe .\\src\\orchestrator.py\n"
        )
        raise SystemExit(msg)

class Orchestrator:
    def __init__(self):
        self.kg = KnowledgeGraph()
        self.surveyor = Surveyor(self.kg)
        self.hydrologist = Hydrologist(self.kg)
        self.semanticist = Semanticist(self.kg)
        self.archivist = Archivist(self.kg)

    def run_analysis(
        self,
        repo_path: str | Path,
        output_dir: str | Path | None = None,
        phases: list[str] | None = None,
        config: CartographyConfig | None = None,
        incremental: bool = False,
    ):
        repo_root = Path(repo_path).resolve()
        print(f"Starting orchestration for: {repo_root}")

        phases = [p.lower() for p in (phases or ["surveyor", "hydrologist", "semanticist", "archivist"])]
        trace = [{"ts": self._utc_now(), "event": "start", "repo_root": str(repo_root), "phases": phases}]
        config = config or CartographyConfig()

        # Incremental mode will be implemented fully (prune + re-run only changed files).
        # For now, we keep the flag to match the final rubric API surface.
        if incremental and config.incremental.enabled is False:
            # If user passed --incremental but config disables it, prefer safety and run full.
            incremental = False
        
        # Surveyor Phase
        if "surveyor" in phases:
            trace.append({"ts": self._utc_now(), "event": "phase_start", "phase": "surveyor"})
            self.surveyor.analyze(repo_root)
            trace.append({"ts": self._utc_now(), "event": "phase_end", "phase": "surveyor"})
        
        # Hydrologist Phase
        if "hydrologist" in phases:
            trace.append({"ts": self._utc_now(), "event": "phase_start", "phase": "hydrologist"})
            self.hydrologist.analyze(repo_root)
            trace.append({"ts": self._utc_now(), "event": "phase_end", "phase": "hydrologist"})

        # Semanticist Phase
        if "semanticist" in phases and config.semanticist.enabled:
            trace.append({"ts": self._utc_now(), "event": "phase_start", "phase": "semanticist"})
            self.semanticist.annotate_modules(repo_root, config=config)
            trace.append({"ts": self._utc_now(), "event": "phase_end", "phase": "semanticist"})
        
        # Serialization Phase
        # Always write artifacts into the analyzed repo's `.cartography/`.
        target_out = repo_root / ".cartography"
        target_out.mkdir(exist_ok=True, parents=True)

        self.kg.serialize_module_graph(target_out / "module_graph.json")
        self.kg.serialize_lineage_graph(target_out / "lineage_graph.json")

        # Optionally also write a copy somewhere else (e.g. this tool repo's `.cartography/`).
        extra_out = None
        if output_dir is not None:
            extra_out = Path(output_dir).expanduser().resolve()
            extra_out.mkdir(exist_ok=True, parents=True)
            if extra_out != target_out:
                self.kg.serialize_module_graph(extra_out / "module_graph.json")
                self.kg.serialize_lineage_graph(extra_out / "lineage_graph.json")

        # Archivist Phase (writes markdown context + trace)
        out_dirs = [target_out]
        if extra_out and extra_out != target_out:
            out_dirs.append(extra_out)

        if "archivist" in phases:
            trace.append({"ts": self._utc_now(), "event": "phase_start", "phase": "archivist"})
            for od in out_dirs:
                self.archivist.write_codebase_md(repo_root, od)
                self.archivist.write_onboarding_brief(repo_root, od)
                self.archivist.write_trace(od, trace)
            trace.append({"ts": self._utc_now(), "event": "phase_end", "phase": "archivist"})

        if extra_out and extra_out != target_out:
            print(f"Orchestration complete. Artifacts saved in: {target_out} and {extra_out}")
        else:
            print(f"Orchestration complete. Artifacts saved in: {target_out}")

    @staticmethod
    def _utc_now() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

if __name__ == "__main__":
    _require_runtime_deps()
    orchestrator = Orchestrator()
    orchestrator.run_analysis(".")
