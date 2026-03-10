import argparse
import sys
from pathlib import Path

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

    repo_path = Path(args.path)
    
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
