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

        if extra_out and extra_out != target_out:
            print(f"Orchestration complete. Artifacts saved in: {target_out} and {extra_out}")
        else:
            print(f"Orchestration complete. Artifacts saved in: {target_out}")

if __name__ == "__main__":
    _require_runtime_deps()
    orchestrator = Orchestrator()
    orchestrator.run_analysis(".")
