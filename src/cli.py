import argparse
import sys
import subprocess
from pathlib import Path
from urllib.parse import urlparse


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
    
    query_parser = subparsers.add_parser("query", help="Interactive Navigator query agent")
    query_parser.add_argument("path", help="Path to the analyzed repository")

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
        from orchestrator import Orchestrator
        orchestrator = Orchestrator()
        orchestrator.run_analysis(repo_path)
    elif args.command == "query":
        print(f"Starting Navigator query session for: {repo_path}")
        # Run Navigator

if __name__ == "__main__":
    main()
