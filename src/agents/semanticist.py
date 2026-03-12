from __future__ import annotations

import sys
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from graph.knowledge_graph import KnowledgeGraph


@dataclass(frozen=True)
class PurposeResult:
    purpose_statement: str
    domain_cluster: str


class Semanticist:
    """
    Interim Semanticist implementation.

    Goal: provide deterministic purpose statements and coarse domain clustering
    without requiring external LLMs. This keeps the "four phases" pipeline
    runnable end-to-end in restricted environments.
    """

    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg

    @staticmethod
    def _domain_cluster_from_path(path: str) -> str:
        parts = [p for p in path.replace("\\", "/").split("/") if p]
        if not parts:
            return "root"
        if parts[0] in {"src", "core", "app"} and len(parts) >= 2:
            return parts[1]
        return parts[0]

    @staticmethod
    def _read_first_docstring(text: str) -> str:
        # Very small heuristic: capture leading triple-quoted string.
        m = re.search(r'^\s*(?P<q>"""|\'\'\')(?P<body>.*?)(?P=q)', text, flags=re.S)
        if not m:
            return ""
        body = m.group("body").strip()
        return re.sub(r"\s+", " ", body)[:240]

    @staticmethod
    def _purpose_from_signals(path: str, node_attrs: Dict[str, Any], file_text: str) -> str:
        language = str(node_attrs.get("language") or "")
        doc = Semanticist._read_first_docstring(file_text)

        if language == "python":
            func_defs = node_attrs.get("function_defs") or []
            class_defs = node_attrs.get("class_defs") or []
            fn_names = [f.get("name") for f in func_defs if isinstance(f, dict) and f.get("name")]
            cls_names = [c.get("name") for c in class_defs if isinstance(c, dict) and c.get("name")]
            bits: List[str] = []
            if cls_names:
                bits.append("classes: " + ", ".join(sorted(set(cls_names))[:6]))
            if fn_names:
                bits.append("functions: " + ", ".join(sorted(set(fn_names))[:8]))
            if doc:
                bits.append("doc: " + doc)
            if bits:
                return f"{path} defines " + "; ".join(bits) + "."
            return f"{path} is a Python module."

        if language == "sql":
            if "{{" in file_text or "{%" in file_text:
                return f"{path} is a SQL model/query template (Jinja detected)."
            return f"{path} is a SQL file."

        if language == "yaml":
            return f"{path} is a YAML configuration file."

        return f"{path} is a source file."

    def annotate_modules(self, repo_root: Path) -> None:
        """
        Adds/updates purpose_statement + domain_cluster on module graph nodes.
        """
        for node_id, attrs in list(self.kg.module_graph.nodes(data=True)):
            try:
                rel = str(node_id)
                file_path = (repo_root / rel).resolve()
                text = ""
                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    text = ""

                domain = self._domain_cluster_from_path(rel)
                purpose = self._purpose_from_signals(rel, attrs, text)
                attrs["domain_cluster"] = domain
                attrs["purpose_statement"] = purpose
            except Exception:
                # Semanticist should not fail the pipeline.
                continue
