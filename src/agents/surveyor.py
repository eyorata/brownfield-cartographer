import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any
import networkx as nx
from datetime import datetime, timezone

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from graph.knowledge_graph import KnowledgeGraph
from models.edges import ImportsEdge
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

    def analyze(self, repo_path: str | Path, only_files: set[str] | None = None, trace: list[dict] | None = None):
        print(f"Surveyor analyzing structure of {repo_path}")

        base_path = Path(repo_path).resolve()
        velocity = self._get_git_velocity(base_path, days=30)
        module_exports: Dict[str, int] = {}

        only_files_norm = None
        if only_files:
            only_files_norm = {str(Path(p).as_posix()) for p in only_files}
        
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
                    "artifacts",
                    "_targets",
                    "_tmp",
                    "node_modules",
                )
            ]
            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix.lower()
                if ext not in {".py", ".sql", ".yml", ".yaml", ".js", ".jsx", ".ts", ".tsx"}:
                    continue

                rel_path = str(file_path.relative_to(base_path)).replace("\\", "/")
                if only_files_norm is not None and rel_path not in only_files_norm:
                    continue
                language = {
                    ".py": "python",
                    ".sql": "sql",
                    ".yml": "yaml",
                    ".yaml": "yaml",
                    ".js": "javascript",
                    ".jsx": "javascript",
                    ".ts": "typescript",
                    ".tsx": "typescript",
                }.get(ext, ext.lstrip("."))

                data: Dict[str, Any] = {}
                public_symbol_count = 0
                if ext == ".py":
                    try:
                        data = self.analyzer.analyze_python_module(str(file_path))
                    except Exception as e:
                        print(f"Failed to analyze python module {file_path}: {e}")
                        data = {}
                    public_symbol_count = len([n for n in data.get("functions", []) if not str(n).startswith("_")]) + len(
                        [n for n in data.get("classes", []) if not str(n).startswith("_")]
                    )
                elif ext in {".js", ".jsx", ".ts", ".tsx"}:
                    try:
                        if ext in {".ts", ".tsx"}:
                            data = self.analyzer.parse_typescript(str(file_path))
                        else:
                            data = self.analyzer.parse_javascript(str(file_path))
                    except Exception as e:
                        print(f"Failed to analyze js/ts module {file_path}: {e}")
                        data = {}

                module_exports[rel_path] = public_symbol_count

                node = ModuleNode(
                    path=rel_path,
                    language=language,
                    change_velocity_30d=velocity.get(rel_path, 0),
                    is_dead_code_candidate=False,  # computed after import graph is built
                    public_symbol_count=public_symbol_count,
                    last_modified=str(int(file_path.stat().st_mtime)) if file_path.exists() else None,
                )
                self.kg.add_module_node(node)

                # Attach analyzer-derived structure for downstream agents (Semanticist/Navigator).
                # Keep this lightweight and schema-adjacent (stored as node attrs, not in ModuleNode schema).
                if ext in {".py", ".js", ".jsx", ".ts", ".tsx"} and data:
                    try:
                        self.kg.module_graph.nodes[rel_path]["import_modules"] = data.get("import_modules") or []
                        if ext == ".py":
                            self.kg.module_graph.nodes[rel_path]["function_defs"] = data.get("function_defs") or []
                            self.kg.module_graph.nodes[rel_path]["class_defs"] = data.get("class_defs") or []
                            self.kg.module_graph.nodes[rel_path]["data_ops"] = data.get("data_ops") or []
                    except Exception:
                        pass
                    if trace is not None:
                        try:
                            trace.append(
                                {
                                    "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    "agent": "surveyor",
                                    "action": "python_structure" if ext == ".py" else "js_ts_structure",
                                    "file": rel_path,
                                    "method": "static",
                                    "confidence": 0.8 if ext == ".py" else 0.7,
                                    "functions": len(data.get("functions") or []) if ext == ".py" else 0,
                                    "classes": len(data.get("classes") or []) if ext == ".py" else 0,
                                    "imports": len(data.get("import_modules") or []),
                                }
                            )
                        except Exception:
                            pass

                if ext == ".py":
                    import_specs = data.get("import_modules") or []
                    if not import_specs:
                        # Back-compat: best-effort resolve from simple import roots.
                        import_specs = [{"kind": "import", "module": m, "level": 0, "names": []} for m in data.get("imports", [])]

                    rel_dir_parts = Path(rel_path).parent.parts
                    if Path(rel_path).name == "__init__.py":
                        rel_dir_parts = Path(rel_path).parent.parts

                    def resolve_module(module_parts, line_range: str = "1-1"):
                        if not module_parts:
                            return
                        candidate = base_path / Path(*module_parts)
                        py_mod = candidate.with_suffix(".py")
                        pkg_init = candidate / "__init__.py"
                        if py_mod.exists():
                            target = str(py_mod.relative_to(base_path)).replace("\\", "/")
                            self.kg.add_import_edge(
                                ImportsEdge(
                                    source_module=rel_path,
                                    target_module=target,
                                    weight=1,
                                    source_file=rel_path,
                                    line_range=line_range,
                                )
                            )
                        elif pkg_init.exists():
                            target = str(pkg_init.relative_to(base_path)).replace("\\", "/")
                            self.kg.add_import_edge(
                                ImportsEdge(
                                    source_module=rel_path,
                                    target_module=target,
                                    weight=1,
                                    source_file=rel_path,
                                    line_range=line_range,
                                )
                            )

                    for spec in import_specs:
                        try:
                            kind = spec.get("kind", "import")
                            module = str(spec.get("module") or "")
                            level = int(spec.get("level") or 0)
                            names = spec.get("names") or []
                            lr = str(spec.get("line_range") or "1-1")
                        except Exception:
                            continue

                        module_parts = [p for p in module.split(".") if p]
                        if level > 0:
                            up = max(0, level - 1)
                            base_parts = list(rel_dir_parts)
                            if up:
                                base_parts = base_parts[:-up] if up <= len(base_parts) else []
                            resolve_module(base_parts + module_parts, line_range=lr)
                            if kind == "from":
                                for name in names:
                                    name_parts = [p for p in str(name).split(".") if p]
                                    resolve_module(base_parts + module_parts + name_parts, line_range=lr)
                        else:
                            resolve_module(module_parts, line_range=lr)
                            if kind == "from":
                                for name in names:
                                    name_parts = [p for p in str(name).split(".") if p]
                                    resolve_module(module_parts + name_parts, line_range=lr)
                elif ext in {".js", ".jsx", ".ts", ".tsx"}:
                    import_specs = data.get("import_modules") or []
                    if not import_specs:
                        continue

                    rel_dir = Path(rel_path).parent

                    def _try_candidates(base_no_ext: Path) -> Path | None:
                        # If the spec includes an extension, check it directly.
                        direct = (base_path / base_no_ext).resolve()
                        if direct.exists() and direct.is_file():
                            return direct

                        exts = [".ts", ".tsx", ".js", ".jsx"]
                        for e in exts:
                            p = (base_path / base_no_ext).with_suffix(e)
                            if p.exists():
                                return p

                        dirp = base_path / base_no_ext
                        if dirp.exists() and dirp.is_dir():
                            for e in exts:
                                idx = dirp / ("index" + e)
                                if idx.exists():
                                    return idx
                        return None

                    for spec in import_specs:
                        try:
                            mod = str(spec.get("module") or "")
                            lr = str(spec.get("line_range") or "1-1")
                        except Exception:
                            continue
                        # Only connect local file-to-file imports.
                        if not mod or not mod.startswith("."):
                            continue

                        base_no_ext = (rel_dir / mod).as_posix()
                        resolved = _try_candidates(Path(base_no_ext))
                        if not resolved:
                            continue
                        try:
                            target_rel = str(resolved.relative_to(base_path)).replace("\\", "/")
                        except Exception:
                            continue
                        self.kg.add_import_edge(
                            ImportsEdge(
                                source_module=rel_path,
                                target_module=target_rel,
                                weight=1,
                                source_file=rel_path,
                                line_range=lr,
                            )
                        )
                        
        try:
            ranks = self._pagerank_power_iteration(self.kg.module_graph)
            for node_id, rank in ranks.items():
                if node_id in self.kg.module_graph.nodes:
                    self.kg.module_graph.nodes[node_id]["pagerank"] = rank
        except Exception as e:
            print(f"PageRank failed or graph is empty: {e}")

        # Attach derived node analytics (dead code, degrees, pagerank).
        for node_id in list(self.kg.module_graph.nodes):
            attrs = self.kg.module_graph.nodes[node_id]
            in_deg = int(self.kg.module_graph.in_degree(node_id))
            out_deg = int(self.kg.module_graph.out_degree(node_id))
            public_defs = module_exports.get(node_id, 0)

            # Heuristic: "exported symbols with no importers" suggests unused leaf modules.
            # Exclude common entrypoints and package inits.
            is_entrypoint = node_id.endswith(("__init__.py", "main.py", "cli.py"))
            is_dead = (public_defs > 0) and (in_deg == 0) and (not is_entrypoint)

            attrs["import_in_degree"] = in_deg
            attrs["import_out_degree"] = out_deg
            attrs["public_symbol_count"] = public_defs
            attrs["is_dead_code_candidate"] = bool(is_dead)
            
        try:
            scc = list(nx.strongly_connected_components(self.kg.module_graph))
            circular_deps = [c for c in scc if len(c) > 1]
            if circular_deps:
                print(f"Found {len(circular_deps)} circular dependencies.")
        except Exception as e:
            pass

        # Summarize top velocity files for downstream consumption.
        if velocity:
            top = sorted(velocity.items(), key=lambda kv: kv[1], reverse=True)[:10]
            self.kg.module_graph.graph["top_velocity_files_30d"] = [{"path": p, "touches": c} for p, c in top]
