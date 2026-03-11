from __future__ import annotations

from pathlib import Path

from agents.surveyor import Surveyor
from agents.hydrologist import Hydrologist
from graph.knowledge_graph import KnowledgeGraph

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
    orchestrator = Orchestrator()
    orchestrator.run_analysis(".")
