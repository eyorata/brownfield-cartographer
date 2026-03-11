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

    def run_analysis(self, repo_path: str | Path):
        repo_root = Path(repo_path).resolve()
        print(f"Starting orchestration for: {repo_root}")
        
        # Surveyor Phase
        self.surveyor.analyze(repo_root)
        
        # Hydrologist Phase
        self.hydrologist.analyze(repo_root)
        
        # Serialization Phase
        # Artifacts belong to the analyzed repo, not the cartographer repo.
        output_dir = repo_root / ".cartography"
        output_dir.mkdir(exist_ok=True)
        
        self.kg.serialize_module_graph(output_dir / "module_graph.json")
        self.kg.serialize_lineage_graph(output_dir / "lineage_graph.json")
        
        print("Orchestration complete. Artifacts saved in .cartography/")

if __name__ == "__main__":
    _require_runtime_deps()
    orchestrator = Orchestrator()
    orchestrator.run_analysis(".")
