import argparse
import sys
import subprocess
from pathlib import Path
from urllib.parse import urlparse

# Allow running from repo root (`python src/cli.py ...`) or directly (`python cli.py ...`)
# without import errors across `agents/`, `analyzers/`, etc.
_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))


def _require_runtime_deps() -> None:
    """
    Fail fast with a helpful message if the user is running with a Python that
    doesn't have this project's deps installed (common when not using .venv).
    """
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
            + "Run using the project venv (recommended):\n"
            + "  .\\.venv\\Scripts\\python.exe .\\src\\cli.py analyze <repo_path>\n\n"
            + "Or install deps with uv:\n"
            + "  uv sync\n"
        )
        raise SystemExit(msg)


def _is_git_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc:
        return False
    # Keep it simple: accept GitHub URLs and plain *.git URLs.
    return "github.com" in parsed.netloc or parsed.path.endswith(".git")


def _clone_github_repo(url: str, dest_root: Path) -> Path:
    """
    Shallow clone into dest_root. Returns path to the local clone.

    Note: In this sandbox environment, cloning may require network approval.
    """
    parsed = urlparse(url)
    # Best-effort name: owner__repo
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    owner = parts[0] if len(parts) >= 1 else "repo"
    repo = parts[1] if len(parts) >= 2 else "target"
    repo = repo.removesuffix(".git")
    slug = f"{owner}__{repo}"

    dest_root.mkdir(parents=True, exist_ok=True)
    dest = (dest_root / slug).resolve()

    if dest.exists() and (dest / ".git").exists():
        return dest

    # Keep it small but useful for analysis.
    cmd = [
        "git",
        "clone",
        "--depth",
        "1",
        "--filter=blob:none",
        "--single-branch",
        url,
        str(dest),
    ]
    subprocess.run(cmd, check=True)
    return dest

def main():
    parser = argparse.ArgumentParser(description="The Brownfield Cartographer")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    analyze_parser = subparsers.add_parser("analyze", help="Run the full analysis pipeline")
    analyze_parser.add_argument("path", help="Path to a local repository or GitHub URL")
    analyze_parser.add_argument("--config", default=None, help="Path to cartography_config.yaml (optional)")
    analyze_parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional second directory to also write artifacts. Primary output always goes to <target_repo>/.cartography. Example: --output-dir .cartography",
    )
    analyze_parser.add_argument(
        "--incremental",
        action="store_true",
        help="Incremental mode (re-analyze changed files only) based on config.diff_range",
    )
    
    query_parser = subparsers.add_parser("query", help="Interactive Navigator query agent")
    query_parser.add_argument("path", help="Path to the analyzed repository")
    query_parser.add_argument(
        "--graph-dir",
        default=None,
        help="Optional directory containing module_graph.json / lineage_graph.json. Defaults to <repo>/.cartography",
    )
    query_parser.add_argument("--config", default=None, help="Path to cartography_config.yaml (optional)")

    serve_parser = subparsers.add_parser("serve", help="Run the local Cartography UI server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    serve_parser.add_argument("--config", default=None, help="Path to cartography_config.yaml (optional)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    repo_path_value = args.path
    if _is_git_url(repo_path_value):
        repo_path = _clone_github_repo(repo_path_value, Path(".cartography") / "_repos")
    else:
        repo_path = Path(repo_path_value)
    
    if args.command == "analyze":
        print(f"Running analysis on: {repo_path}")
        _require_runtime_deps()
        from config import load_config
        from orchestrator import Orchestrator

        cfg = load_config(args.config)
        orchestrator = Orchestrator()
        orchestrator.run_analysis(repo_path, output_dir=args.output_dir, config=cfg, incremental=bool(args.incremental))
    elif args.command == "query":
        print(f"Starting Navigator query session for: {repo_path}")
        _require_runtime_deps()
        from config import load_config
        from agents.navigator import Navigator
        from graph.knowledge_graph import KnowledgeGraph

        repo_root = Path(repo_path).resolve()
        graph_dir = Path(args.graph_dir).resolve() if args.graph_dir else (repo_root / ".cartography")

        cfg = load_config(args.config)
        kg = KnowledgeGraph()
        kg.load_from_dir(graph_dir)
        nav = Navigator(kg, repo_root=repo_root, config=cfg)

        print(f"Loaded graphs from: {graph_dir}")
        print("Type 'help' for commands. Type 'exit' to quit.")

        while True:
            try:
                raw = input("cartography> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("")
                break

            if not raw:
                continue

            if raw in {"exit", "quit"}:
                break

                if raw in {"help", "?"}:
                    print("Commands:")
                    print("  stats")
                    print("  sources [N]")
                    print("  sinks [N]")
                    print("  blast <node>")
                    print("  trace up <node> [depth] | trace down <node> [depth]")
                    print("  module <relative/path.py>")
                    print("  ask <natural language question>  (LangGraph/LLM)")
                    continue

            parts = raw.split()
            cmd = parts[0].lower()

            try:
                if cmd == "stats":
                    print(nav.stats())
                elif cmd == "sources":
                    n = int(parts[1]) if len(parts) >= 2 else 25
                    for s in nav.list_sources(limit=n):
                        print(s)
                elif cmd == "sinks":
                    n = int(parts[1]) if len(parts) >= 2 else 25
                    for s in nav.list_sinks(limit=n):
                        print(s)
                elif cmd == "blast":
                    if len(parts) < 2:
                        print("Usage: blast <node>")
                        continue
                    node = " ".join(parts[1:])
                    results = nav.blast_radius(node)
                    for r in results:
                        p = r.get("path") or []
                        print(f"- {r.get('node')}  path={' -> '.join(map(str, p))}")
                elif cmd == "trace":
                    if len(parts) < 3:
                        print("Usage: trace up|down <node> [depth]")
                        continue
                    direction = parts[1].lower()
                    node = parts[2]
                    depth = int(parts[3]) if len(parts) >= 4 else 6
                    paths = nav.trace_lineage(node=node, direction=direction, max_depth=depth)
                    if not paths:
                        print("(no paths found)")
                        continue
                    for tp in paths:
                        print(" -> ".join(tp.path))
                elif cmd == "module":
                    if len(parts) < 2:
                        print("Usage: module <relative/path.py>")
                        continue
                    mod = parts[1]
                    info = nav.module_summary(mod)
                    if not info.get("found"):
                        print("Module not found in graph.")
                        continue
                    attrs = info.get("attrs") or {}
                    keys = {
                        "language",
                        "pagerank",
                        "change_velocity_30d",
                        "domain_cluster",
                        "is_dead_code_candidate",
                        "purpose_statement",
                    }
                    print("attrs:", {k: attrs.get(k) for k in sorted(keys) if k in attrs})
                    print("imports_out:")
                    for x in info.get("imports_out") or []:
                        print(f"  - {x.get('to')}")
                    print("imports_in:")
                    for x in info.get("imports_in") or []:
                        print(f"  - {x.get('from')}")
                elif cmd == "ask":
                    q = raw[len("ask") :].strip()
                    if not q:
                        print("Usage: ask <question>")
                        continue
                    print(nav.ask(q))
                else:
                    # If LangGraph is enabled, treat unknown input as a natural language question.
                    if cfg.navigator.use_langgraph:
                        print(nav.ask(raw))
                    else:
                        print("Unknown command. Type 'help'.")
            except Exception as e:
                print(f"Error: {e}")
    elif args.command == "serve":
        _require_runtime_deps()
        from ui_server import serve

        serve(host=args.host, port=args.port)

if __name__ == "__main__":
    main()
