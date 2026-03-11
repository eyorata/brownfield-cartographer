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

    def _get_git_velocity(self, repo_path: Path, days: int = 30) -> Dict[str, int]:
        velocity = {}
        try:
            # Git expects a human-ish time expression (e.g. "30 days ago"), not "30.days".
            # Also, some environments (like sandboxed agents) can trigger safe.directory checks.
            cmd = [
                "git",
                "-c",
                f"safe.directory={repo_path.resolve()}",
                "log",
                f"--since={days} days ago",
                "--name-only",
                "--pretty=format:",
            ]
            result = subprocess.run(cmd, cwd=str(repo_path), capture_output=True, text=True, check=True)
            for line in result.stdout.splitlines():
                line = line.strip()
                if line:
                    velocity[line] = velocity.get(line, 0) + 1
        except Exception as e:
            print(f"Failed to get git velocity: {e}")
        return velocity

    def _pagerank_power_iteration(
        self,
        graph: nx.DiGraph,
        alpha: float = 0.85,
        max_iter: int = 100,
        tol: float = 1.0e-6,
    ) -> Dict[str, float]:
        nodes = list(graph.nodes)
        n = len(nodes)
        if n == 0:
            return {}

        rank = {node: 1.0 / n for node in nodes}
        out_weight_sum: Dict[str, float] = {}
        dangling = []

        for node in nodes:
            total = 0.0
            for _, __, data in graph.out_edges(node, data=True):
                total += float(data.get("weight", 1.0))
            out_weight_sum[node] = total
            if total == 0.0:
                dangling.append(node)

        base = (1.0 - alpha) / n

        for _ in range(max_iter):
            new_rank = {node: base for node in nodes}
            dangling_mass = alpha * sum(rank[node] for node in dangling) / n if dangling else 0.0

            for src in nodes:
                total = out_weight_sum[src]
                if total == 0.0:
                    continue

                src_rank = rank[src]
                for _, dst, data in graph.out_edges(src, data=True):
                    weight = float(data.get("weight", 1.0))
                    new_rank[dst] += alpha * src_rank * (weight / total)

            if dangling_mass:
                for node in nodes:
                    new_rank[node] += dangling_mass

            err = sum(abs(new_rank[node] - rank[node]) for node in nodes)
            rank = new_rank
            if err < tol:
                break

        return rank

    def analyze(self, repo_path: str | Path):
        print(f"Surveyor analyzing structure of {repo_path}")
        
        base_path = Path(repo_path).resolve()
        velocity = self._get_git_velocity(base_path, days=30)
        
        for root, dirs, files in os.walk(base_path):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d
                not in (
                    "venv",
                    "__pycache__",
                    "env",
                    ".venv",
                    ".cartography",
                    "_targets",
                    "_tmp",
                    "node_modules",
                )
            ]
            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix.lower()
                if ext not in {".py", ".sql", ".yml", ".yaml"}:
                    continue

                rel_path = str(file_path.relative_to(base_path)).replace("\\", "/")
                language = {
                    ".py": "python",
                    ".sql": "sql",
                    ".yml": "yaml",
                    ".yaml": "yaml",
                }.get(ext, ext.lstrip("."))

                data: Dict[str, Any] = {}
                is_dead = False
                if ext == ".py":
                    data = self.analyzer.analyze_python_module(str(file_path))
                    is_dead = (len(data.get("functions", [])) == 0 and len(data.get("classes", [])) == 0)

                node = ModuleNode(
                    path=rel_path,
                    language=language,
                    change_velocity_30d=velocity.get(rel_path, 0),
                    is_dead_code_candidate=is_dead,
                )
                self.kg.module_graph.add_node(rel_path, **node.dict())

                if ext == ".py":
                    for imp in data.get("imports", []):
                        # Only add edges to modules that exist locally in the repo.
                        candidate = base_path / Path(*imp.split("."))
                        py_mod = candidate.with_suffix(".py")
                        pkg_init = candidate / "__init__.py"
                        if py_mod.exists():
                            target = str(py_mod.relative_to(base_path)).replace("\\", "/")
                            self.kg.module_graph.add_edge(rel_path, target, weight=1)
                        elif pkg_init.exists():
                            target = str(pkg_init.relative_to(base_path)).replace("\\", "/")
                            self.kg.module_graph.add_edge(rel_path, target, weight=1)
                        
        try:
            ranks = self._pagerank_power_iteration(self.kg.module_graph)
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
