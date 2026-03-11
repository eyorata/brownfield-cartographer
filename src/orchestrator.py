from __future__ import annotations

import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from agents.surveyor import Surveyor
from agents.hydrologist import Hydrologist
from graph.knowledge_graph import KnowledgeGraph


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

    def run_analysis(self, repo_path: str | Path, output_dir: str | Path | None = None):
        repo_root = Path(repo_path).resolve()
        print(f"Starting orchestration for: {repo_root}")
        
        # Surveyor Phase
        self.surveyor.analyze(repo_root)
        
        # Hydrologist Phase
        self.hydrologist.analyze(repo_root)
        
        # Serialization Phase
        if output_dir is None:
            # Default: artifacts belong to the analyzed repo.
            out_root = repo_root / ".cartography"
        else:
            # Allows writing artifacts into this tool repo's `.cartography/` (or any other path).
            out_root = Path(output_dir).expanduser().resolve()
        out_root.mkdir(exist_ok=True, parents=True)
        
        self.kg.serialize_module_graph(out_root / "module_graph.json")
        self.kg.serialize_lineage_graph(out_root / "lineage_graph.json")
        
        print(f"Orchestration complete. Artifacts saved in: {out_root}")

if __name__ == "__main__":
    _require_runtime_deps()
    orchestrator = Orchestrator()
    orchestrator.run_analysis(".")
