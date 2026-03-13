from __future__ import annotations

import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from agents.surveyor import Surveyor
from agents.hydrologist import Hydrologist
from agents.semanticist import Semanticist
from agents.archivist import Archivist
from graph.knowledge_graph import KnowledgeGraph
from config import CartographyConfig
import subprocess
import json
import shutil


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
        self.semanticist = Semanticist(self.kg)
        self.archivist = Archivist(self.kg)

    def run_analysis(
        self,
        repo_path: str | Path,
        output_dir: str | Path | None = None,
        phases: list[str] | None = None,
        config: CartographyConfig | None = None,
        incremental: bool = False,
    ):
        repo_root = Path(repo_path).resolve()
        print(f"Starting orchestration for: {repo_root}")

        phases = [p.lower() for p in (phases or ["surveyor", "hydrologist", "semanticist", "archivist"])]
        trace: list[dict] = [{"ts": self._utc_now(), "event": "start", "repo_root": str(repo_root), "phases": phases}]
        config = config or CartographyConfig()

        # Incremental mode will be implemented fully (prune + re-run only changed files).
        changed_files: set[str] | None = None
        if incremental:
            if not config.incremental.enabled:
                incremental = False
            else:
                # Prefer "since last successful run" if metadata exists; else fall back to config.diff_range.
                prev = self._read_run_metadata(repo_root).get("head_sha")
                head = self._git_head_sha(repo_root)
                if prev and head and prev != head:
                    changed_files = self._git_changed_files(repo_root, f"{prev}..{head}")
                    trace.append(
                        {
                            "ts": self._utc_now(),
                            "event": "incremental",
                            "mode": "since_last_run",
                            "prev_sha": prev,
                            "head_sha": head,
                            "changed_files": sorted(changed_files)[:500],
                        }
                    )
                else:
                    changed_files = self._git_changed_files(repo_root, config.incremental.diff_range)
                if not changed_files:
                    incremental = False
                else:
                    # If we used config.diff_range, log it for reproducibility.
                    if not (prev and head and prev != head):
                        trace.append(
                            {
                                "ts": self._utc_now(),
                                "event": "incremental",
                                "mode": "diff_range",
                                "diff_range": config.incremental.diff_range,
                                "changed_files": sorted(changed_files)[:500],
                            }
                        )
        
        # If incremental, load previous graphs from target output and prune affected nodes/edges.
        target_out = repo_root / ".cartography"
        if incremental:
            try:
                self.kg.load_from_dir(target_out)
            except Exception:
                pass
            try:
                self.kg.prune_changed_files(changed_files or set())
            except Exception:
                pass

        # Surveyor Phase
        if "surveyor" in phases:
            trace.append({"ts": self._utc_now(), "event": "phase_start", "phase": "surveyor"})
            self.surveyor.analyze(repo_root, only_files=changed_files, trace=trace)
            trace.append({"ts": self._utc_now(), "event": "phase_end", "phase": "surveyor"})
            # Preserve partial results in case a later phase fails.
            target_out.mkdir(exist_ok=True, parents=True)
            self.kg.serialize_module_graph(target_out / "module_graph.json")

        # Hydrologist Phase
        if "hydrologist" in phases:
            trace.append({"ts": self._utc_now(), "event": "phase_start", "phase": "hydrologist"})
            self.hydrologist.analyze(repo_root, only_files=changed_files, trace=trace)
            trace.append({"ts": self._utc_now(), "event": "phase_end", "phase": "hydrologist"})
            target_out.mkdir(exist_ok=True, parents=True)
            self.kg.serialize_lineage_graph(target_out / "lineage_graph.json")

        # Semanticist Phase
        if "semanticist" in phases and config.semanticist.enabled:
            trace.append({"ts": self._utc_now(), "event": "phase_start", "phase": "semanticist"})
            self.semanticist.run(repo_root, config=config, trace=trace, output_dir=target_out, only_files=changed_files)
            trace.append({"ts": self._utc_now(), "event": "phase_end", "phase": "semanticist"})
            target_out.mkdir(exist_ok=True, parents=True)
            self.kg.serialize_module_graph(target_out / "module_graph.json")

        # Serialization Phase
        # Always write artifacts into the analyzed repo's `.cartography/`.
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
                # Copy semantic index if present (built by Semanticist).
                try:
                    si = target_out / "semantic_index.json"
                    if si.exists():
                        shutil.copy2(si, extra_out / "semantic_index.json")
                except Exception:
                    pass

        # Archivist Phase (writes markdown context + trace)
        out_dirs = [target_out]
        if extra_out and extra_out != target_out:
            out_dirs.append(extra_out)

        if "archivist" in phases:
            trace.append({"ts": self._utc_now(), "event": "phase_start", "phase": "archivist"})
            for od in out_dirs:
                trace.append(
                    {
                        "ts": self._utc_now(),
                        "agent": "archivist",
                        "action": "write_codebase_md",
                        "method": "static",
                        "confidence": 0.9,
                        "output": str((Path(od) / "CODEBASE.md").as_posix()),
                    }
                )
                self.archivist.write_codebase_md(repo_root, od)
                trace.append(
                    {
                        "ts": self._utc_now(),
                        "agent": "archivist",
                        "action": "write_onboarding_brief",
                        "method": "static",
                        "confidence": 0.9,
                        "output": str((Path(od) / "onboarding_brief.md").as_posix()),
                    }
                )
                self.archivist.write_onboarding_brief(repo_root, od)
                trace.append(
                    {
                        "ts": self._utc_now(),
                        "agent": "archivist",
                        "action": "write_trace",
                        "method": "static",
                        "confidence": 0.95,
                        "output": str((Path(od) / "cartography_trace.jsonl").as_posix()),
                    }
                )
                self.archivist.write_trace(od, trace)
            trace.append({"ts": self._utc_now(), "event": "phase_end", "phase": "archivist"})

        # Record metadata for incremental runs.
        try:
            head = self._git_head_sha(repo_root)
            if head:
                self._write_run_metadata(repo_root, {"head_sha": head, "ts": self._utc_now()})
        except Exception:
            pass

        if extra_out and extra_out != target_out:
            print(f"Orchestration complete. Artifacts saved in: {target_out} and {extra_out}")
        else:
            print(f"Orchestration complete. Artifacts saved in: {target_out}")

    @staticmethod
    def _utc_now() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _git_head_sha(repo_root: Path) -> str:
        try:
            cmd = ["git", "-c", f"safe.directory={repo_root.resolve()}", "rev-parse", "HEAD"]
            r = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, check=True)
            return r.stdout.strip()
        except Exception:
            return ""

    @staticmethod
    def _git_changed_files(repo_root: Path, diff_range: str) -> set[str]:
        """
        Returns repo-relative POSIX paths changed in the given git diff range.
        """
        try:
            cmd = [
                "git",
                "-c",
                f"safe.directory={repo_root.resolve()}",
                "diff",
                "--name-only",
                diff_range,
            ]
            r = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, check=True)
            out = set()
            for line in r.stdout.splitlines():
                p = line.strip().replace("\\", "/")
                if p:
                    out.add(p)
            return out
        except Exception:
            return set()

    @staticmethod
    def _read_run_metadata(repo_root: Path) -> dict:
        p = repo_root / ".cartography" / "run_metadata.json"
        if not p.exists():
            return {}
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _write_run_metadata(repo_root: Path, data: dict) -> None:
        p = repo_root / ".cartography" / "run_metadata.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    _require_runtime_deps()
    orchestrator = Orchestrator()
    orchestrator.run_analysis(".")
