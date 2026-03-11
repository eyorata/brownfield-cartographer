import os
import subprocess
from pathlib import Path
from typing import Dict, Any
import networkx as nx
from graph.knowledge_graph import KnowledgeGraph
from models.nodes import ModuleNode
from analyzers.tree_sitter_analyzer import TreeSitterAnalyzer

class Surveyor:
    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg
        self.analyzer = TreeSitterAnalyzer()

    def _get_git_velocity(self, repo_path: str, days: int = 30) -> Dict[str, int]:
        velocity = {}
        try:
            cmd = ["git", "log", f"--since={days}.days", "--name-only", "--pretty=format:"]
            result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, check=True)
            for line in result.stdout.splitlines():
                line = line.strip()
                if line:
                    velocity[line] = velocity.get(line, 0) + 1
        except Exception as e:
            print(f"Failed to get git velocity: {e}")
        return velocity

    def analyze(self, repo_path: str):
        print(f"Surveyor analyzing structure of {repo_path}")
        
        velocity = self._get_git_velocity(repo_path, days=30)
        base_path = Path(repo_path)
        
        for root, dirs, files in os.walk(base_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('venv', '__pycache__', 'env', '.venv')]
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    rel_path = str(file_path.relative_to(base_path)).replace("\\", "/")
                    
                    data = self.analyzer.analyze_python_module(str(file_path))
                    
                    node = ModuleNode(
                        path=rel_path,
                        language="python",
                        change_velocity_30d=velocity.get(rel_path, 0),
                        is_dead_code_candidate=(len(data.get("functions", [])) == 0 and len(data.get("classes", [])) == 0)
                    )
                    
                    self.kg.module_graph.add_node(rel_path, **node.dict())
                    
                    for imp in data.get("imports", []):
                        target = imp.replace('.', '/') + ".py"
                        self.kg.module_graph.add_edge(rel_path, target, weight=1)
                        
        try:
            ranks = nx.pagerank(self.kg.module_graph, weight='weight')
            for node_id, rank in ranks.items():
                if node_id in self.kg.module_graph.nodes:
                    self.kg.module_graph.nodes[node_id]['pagerank'] = rank
        except Exception as e:
            print(f"PageRank failed or graph is empty: {e}")
            
        try:
            scc = list(nx.strongly_connected_components(self.kg.module_graph))
            circular_deps = [c for c in scc if len(c) > 1]
            if circular_deps:
                print(f"Found {len(circular_deps)} circular dependencies.")
        except Exception as e:
            pass
