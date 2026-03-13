from __future__ import annotations

import sys
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple, Optional
import math
from datetime import datetime, timezone

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from config import CartographyConfig
from graph.knowledge_graph import KnowledgeGraph
from llm import ChatMessage, OpenAICompatClient
from graph.semantic_index import SemanticIndex, embed_texts


@dataclass(frozen=True)
class PurposeResult:
    purpose_statement: str
    domain_cluster: str


@dataclass(frozen=True)
class Citation:
    file: str
    line_range: str
    snippet: str


class ContextWindowBudget:
    """
    Very small context budgeting helper.

    We approximate tokens as chars/4 (good enough to avoid blowing up local-model contexts).
    """

    def __init__(self, token_budget: int):
        self.token_budget = int(token_budget)
        self.used_tokens = 0
        self.sections: List[Dict[str, Any]] = []

    @staticmethod
    def _approx_tokens(text: str) -> int:
        return max(1, int(len(text) / 4))

    def remaining(self) -> int:
        return max(0, self.token_budget - self.used_tokens)

    def try_add(self, title: str, text: str, citations: Optional[List[Citation]] = None) -> bool:
        t = self._approx_tokens(text)
        if self.used_tokens + t > self.token_budget:
            return False
        self.used_tokens += t
        self.sections.append(
            {
                "title": title,
                "text": text,
                "citations": citations or [],
                "tokens": t,
            }
        )
        return True

    def render(self) -> str:
        out: List[str] = []
        for s in self.sections:
            out.append(f"## {s['title']}")
            out.append(s["text"].strip())
            if s.get("citations"):
                out.append("Citations:")
                for c in s["citations"]:
                    out.append(f"- {c.file}:{c.line_range}")
            out.append("")
        return "\n".join(out).strip() + "\n"

@dataclass
class LLMBudget:
    max_total_tokens: int
    used_tokens: int = 0
    calls: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.calls is None:
            self.calls = []

    @staticmethod
    def _approx_tokens(text: str) -> int:
        return max(1, int(len(text or "") / 4))

    def choose_model(self, *, config: CartographyConfig, task: str) -> str:
        cheap = config.llm.cheap_model or config.llm.model
        expensive = config.llm.expensive_model or config.llm.model
        if task in {"day_one", "drift"}:
            return expensive
        return cheap

    def spend(self, *, kind: str, model: str, prompt: str, response: str) -> None:
        t = self._approx_tokens(prompt) + self._approx_tokens(response)
        self.used_tokens += int(t)
        self.calls.append({"kind": kind, "model": model, "tokens": int(t)})


class Semanticist:
    """
    Semanticist agent: purpose statements, doc drift detection, and Day-One question answering.

    This implementation is designed to work with a local LM Studio model via an OpenAI-compatible API.
    It degrades gracefully when the LLM is unavailable (deterministic fallbacks still populate fields).
    """

    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

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
    def _read_lines_with_numbers(file_path: Path, start: int, end: int) -> Tuple[str, str]:
        """
        Returns (line_range, snippet) with 1-based lines inclusive.
        """
        try:
            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            return "1-1", ""
        start = max(1, int(start))
        end = max(start, int(end))
        end = min(end, len(lines))
        chunk = lines[start - 1 : end]
        snippet = "\n".join([f"{i+start:4d}: {ln}" for i, ln in enumerate(chunk)])
        return f"{start}-{end}", snippet

    @staticmethod
    def _extract_signal_summary(node_attrs: Dict[str, Any]) -> str:
        func_defs = node_attrs.get("function_defs") or []
        class_defs = node_attrs.get("class_defs") or []
        data_ops = node_attrs.get("data_ops") or []

        fn_names = [f.get("name") for f in func_defs if isinstance(f, dict) and f.get("name")]
        cls_names = [c.get("name") for c in class_defs if isinstance(c, dict) and c.get("name")]

        ops = []
        for op in data_ops:
            if isinstance(op, dict) and op.get("type"):
                ops.append(str(op.get("type")))

        bits: List[str] = []
        if cls_names:
            bits.append("classes=" + ", ".join(sorted(set(cls_names))[:8]))
        if fn_names:
            bits.append("functions=" + ", ".join(sorted(set(fn_names))[:12]))
        if ops:
            bits.append("data_ops=" + ", ".join(sorted(set(ops))[:10]))
        return "; ".join(bits)

    @staticmethod
    def _doc_drift_heuristic(file_text: str, node_attrs: Dict[str, Any]) -> Tuple[float, List[str]]:
        """
        Heuristic doc drift detection (fast, always available).
        Returns (score 0..1, flags).
        """
        doc = Semanticist._read_first_docstring(file_text)
        func_defs = node_attrs.get("function_defs") or []
        class_defs = node_attrs.get("class_defs") or []
        fn_names = {str(f.get("name")) for f in func_defs if isinstance(f, dict) and f.get("name")}
        cls_names = {str(c.get("name")) for c in class_defs if isinstance(c, dict) and c.get("name")}

        flags: List[str] = []
        if not doc and (fn_names or cls_names):
            flags.append("no_docstring")
            return 0.6, flags
        if not doc:
            return 0.0, flags

        doc_l = doc.lower()
        present = 0
        total = 0
        for name in sorted(fn_names | cls_names):
            if name.startswith("_"):
                continue
            total += 1
            if name.lower() in doc_l:
                present += 1
        if total >= 6 and present == 0:
            flags.append("doc_missing_public_symbols")
            return 0.7, flags
        if total >= 6 and present / max(1, total) < 0.15:
            flags.append("doc_mentions_few_symbols")
            return 0.4, flags
        return 0.1 if total else 0.0, flags

    @staticmethod
    def _purpose_from_signals(path: str, node_attrs: Dict[str, Any], file_text: str) -> str:
        language = str(node_attrs.get("language") or "")

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

    def annotate_modules(
        self,
        repo_root: Path,
        config: CartographyConfig | None = None,
        trace: list[dict] | None = None,
        output_dir: Path | None = None,
    ) -> None:
        """
        Adds/updates purpose_statement + domain_cluster on module graph nodes.
        """
        config = config or CartographyConfig()
        output_dir = output_dir or (repo_root / ".cartography")

        llm_client = OpenAICompatClient(
            base_url=config.llm.base_url,
            api_key=config.llm.api_key,
            timeout_s=config.llm.timeout_s,
        )
        if not llm_client.is_available(timeout_s=3):
            llm_client = None

        budget = LLMBudget(max_total_tokens=int(config.llm.max_total_tokens))
        self.kg.module_graph.graph["llm_usage"] = {"max_total_tokens": budget.max_total_tokens, "used_tokens": 0, "calls": []}

        # ---- Build semantic index and embedding-based domain clusters ----
        module_texts: List[Tuple[str, str]] = []
        for node_id, attrs in self.kg.module_graph.nodes(data=True):
            rel = str(node_id)
            fp = (repo_root / rel).resolve()
            snippet = ""
            try:
                if fp.exists():
                    snippet = "\n".join(fp.read_text(encoding="utf-8", errors="ignore").splitlines()[:120])
            except Exception:
                snippet = ""
            signals = self._extract_signal_summary(dict(attrs))
            module_texts.append((rel, f"{rel}\n{signals}\n{snippet}"))

        module_texts = module_texts[: int(config.semanticist.max_semantic_index_modules)]

        idx: SemanticIndex | None = None
        if config.semanticist.semantic_index:
            try:
                idx = SemanticIndex.build(
                    module_texts=module_texts,
                    client=llm_client,
                    model=config.llm.cheap_model or config.llm.model,
                )
                idx.save(output_dir / "semantic_index.json")
                if trace is not None:
                    trace.append(
                        {
                            "ts": self._utc_now(),
                            "agent": "semanticist",
                            "action": "semantic_index",
                            "method": "embedding" if llm_client is not None else "hash_embedding",
                            "confidence": 0.65,
                            "entries": len(idx.entries),
                            "output": str((output_dir / "semantic_index.json").as_posix()),
                        }
                    )
            except Exception:
                idx = None

        def _kmeans_cosine(vectors: List[List[float]], k: int, max_iter: int = 15) -> List[int]:
            n = len(vectors)
            if n == 0:
                return []
            k = max(1, min(int(k), n))
            centroids: List[List[float]] = []
            for i in range(k):
                idx0 = int(round(i * (n - 1) / max(1, (k - 1))))
                centroids.append(list(vectors[idx0]))

            def _cos(a: List[float], b: List[float]) -> float:
                dot = 0.0
                na = 0.0
                nb = 0.0
                for x, y in zip(a, b):
                    dot += float(x) * float(y)
                    na += float(x) * float(x)
                    nb += float(y) * float(y)
                if na <= 0.0 or nb <= 0.0:
                    return 0.0
                return dot / (math.sqrt(na) * math.sqrt(nb))

            assign = [0] * n
            for _ in range(max_iter):
                changed = False
                for i, v in enumerate(vectors):
                    best = 0
                    best_s = -1.0
                    for ci, c in enumerate(centroids):
                        s = _cos(v, c)
                        if s > best_s:
                            best_s = s
                            best = ci
                    if assign[i] != best:
                        assign[i] = best
                        changed = True
                if not changed:
                    break

                dim = len(vectors[0]) if vectors else 0
                sums = [[0.0] * dim for _ in range(k)]
                counts = [0] * k
                for a, v in zip(assign, vectors, strict=False):
                    counts[a] += 1
                    for j in range(dim):
                        sums[a][j] += float(v[j])
                for ci in range(k):
                    if counts[ci] == 0:
                        continue
                    c = [x / counts[ci] for x in sums[ci]]
                    norm = math.sqrt(sum(x * x for x in c)) or 1.0
                    centroids[ci] = [x / norm for x in c]
            return assign

        def _label_clusters(paths: List[str], assignments: List[int]) -> Dict[int, str]:
            stop = {"src", "test", "tests", "py", "sql", "yaml", "yml", "__init__", "main", "cli"}
            counts: Dict[int, Dict[str, int]] = {}
            for p, a in zip(paths, assignments, strict=False):
                toks = re.findall(r"[A-Za-z_][A-Za-z0-9_]{1,40}", p.replace("\\", "/").lower())
                for t in toks:
                    if t in stop or t.isdigit():
                        continue
                    counts.setdefault(int(a), {})[t] = counts.setdefault(int(a), {}).get(t, 0) + 1
            labels: Dict[int, str] = {}
            for a, c in counts.items():
                top = sorted(c.items(), key=lambda kv: kv[1], reverse=True)[:3]
                name = "-".join([t for t, _ in top[:2]]) if top else f"cluster-{a}"
                labels[a] = name or f"cluster-{a}"
            return labels

        # Apply embedding-based domain clusters to all nodes (fallback to path heuristic if clustering fails).
        try:
            paths = [p for p, _ in module_texts]
            vectors = [e.embedding for e in idx.entries] if idx is not None else embed_texts([t for _, t in module_texts])
            n = len(vectors)
            if n >= 8:
                k = min(12, max(2, int(round(math.sqrt(n / 2)))))
                assignments = _kmeans_cosine(vectors, k=k)
                labels = _label_clusters(paths, assignments)
                for rel, a in zip(paths, assignments, strict=False):
                    if rel in self.kg.module_graph.nodes:
                        self.kg.module_graph.nodes[rel]["domain_cluster"] = labels.get(int(a), f"cluster-{a}")
                        self.kg.module_graph.nodes[rel]["domain_cluster_method"] = "embedding"
        except Exception:
            pass

        # Choose a subset of modules for LLM upgrades (purpose/drift), biased by PageRank + velocity.
        ranked = []
        for node_id, attrs in self.kg.module_graph.nodes(data=True):
            pr = float(attrs.get("pagerank") or 0.0)
            vel = int(attrs.get("change_velocity_30d") or 0)
            ranked.append((pr * 1_000_000.0 + vel, str(node_id)))
        ranked.sort(reverse=True)
        llm_targets = {p for _, p in ranked[: max(1, int(config.semanticist.max_llm_modules))]}

        for node_id, attrs in list(self.kg.module_graph.nodes(data=True)):
            try:
                rel = str(node_id)
                file_path = (repo_root / rel).resolve()
                text = ""
                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    text = ""

                # Fallback domain cluster if embedding clustering didn't run.
                if not attrs.get("domain_cluster"):
                    attrs["domain_cluster"] = self._domain_cluster_from_path(rel)
                    attrs["domain_cluster_method"] = "path"

                purpose = self._purpose_from_signals(rel, attrs, text)
                attrs["purpose_statement"] = purpose
                attrs["purpose_method"] = "heuristic"

                if config.semanticist.doc_drift_detection and attrs.get("language") == "python":
                    drift_score, drift_flags = self._doc_drift_heuristic(text, attrs)
                    attrs["doc_drift_score"] = float(drift_score)
                    attrs["doc_drift_flags"] = drift_flags
                    attrs["doc_drift_method"] = "heuristic"

                # LLM upgrades for a limited subset (purpose statement refinement + structured drift).
                if llm_client is not None and rel in llm_targets and file_path.exists():
                    lr, snippet = self._read_lines_with_numbers(file_path, 1, 120)
                    signals = self._extract_signal_summary(attrs)
                    doc = self._read_first_docstring(text)
                    sys_msg = (
                        "You are a codebase cartographer.\n"
                        "Generate a 1-sentence purpose statement grounded ONLY in implementation details.\n"
                        "Ignore docstrings when generating purpose.\n"
                        "Then compare your purpose statement to the docstring and report documentation drift.\n"
                        "Output strict JSON only with keys:\n"
                        "- purpose_statement: string\n"
                        "- doc_drift: {severity:'none'|'low'|'medium'|'high', contradictions:[string], flags:[string]}\n"
                    )
                    user_msg = (
                        f"FILE: {rel}\n"
                        f"LANG: {attrs.get('language')}\n"
                        f"SIGNALS: {signals}\n"
                        f"DOCSTRING (for drift comparison only): {doc}\n\n"
                        f"EXCERPT ({lr}):\n{snippet}\n"
                    )
                    try:
                        model = budget.choose_model(config=config, task="drift")
                        out = llm_client.chat_completions(
                            model=model,
                            messages=[ChatMessage(role="system", content=sys_msg), ChatMessage(role="user", content=user_msg)],
                            temperature=config.llm.temperature,
                            max_tokens=min(700, int(config.llm.max_tokens)),
                            response_format={"type": "json_object"},
                        )
                        import json as _json

                        parsed = _json.loads(out)
                        ps = str(parsed.get("purpose_statement") or "").strip()
                        if ps:
                            attrs["purpose_statement"] = ps
                            attrs["purpose_method"] = "llm"

                        drift = parsed.get("doc_drift")
                        if isinstance(drift, dict):
                            sev = str(drift.get("severity") or "").strip()
                            if sev:
                                attrs["doc_drift_severity"] = sev
                                attrs["doc_drift_method"] = "llm"
                            flags = drift.get("flags")
                            if isinstance(flags, list):
                                attrs["doc_drift_flags"] = [str(x) for x in flags if str(x).strip()]
                            contr = drift.get("contradictions")
                            if isinstance(contr, list):
                                attrs["doc_drift_contradictions"] = [str(x) for x in contr if str(x).strip()][:10]

                        budget.spend(kind="module_purpose_drift", model=model, prompt=sys_msg + "\n" + user_msg, response=out)
                        self.kg.module_graph.graph["llm_usage"] = {
                            "max_total_tokens": budget.max_total_tokens,
                            "used_tokens": budget.used_tokens,
                            "calls": budget.calls[-250:],
                        }
                        if trace is not None:
                            trace.append(
                                {
                                    "ts": self._utc_now(),
                                    "agent": "semanticist",
                                    "action": "annotate_module_llm",
                                    "file": rel,
                                    "method": "llm",
                                    "confidence": 0.55,
                                    "model": model,
                                    "citations": [f"{rel}:{lr}"],
                                }
                            )
                    except Exception:
                        pass
            except Exception:
                continue

    def answer_day_one_questions(self, repo_root: Path, config: CartographyConfig | None = None, trace: list[dict] | None = None) -> None:
        """
        Populate repo-level Day-One answers into graph metadata:
        self.kg.module_graph.graph["day_one_answers"] = {...}

        Includes file:line citations when possible.
        """
        config = config or CartographyConfig()
        llm_client = OpenAICompatClient(
            base_url=config.llm.base_url,
            api_key=config.llm.api_key,
            timeout_s=config.llm.timeout_s,
        )
        if not llm_client.is_available(timeout_s=3):
            self.kg.module_graph.graph["day_one_answers"] = {
                "error": "LLM unavailable for day-one answers. Start LM Studio server and re-run semanticist.",
            }
            return

        # Evidence selection: top modules by pagerank + top velocity + lineage sources/sinks.
        top_mods = sorted(
            [
                (float(a.get("pagerank") or 0.0), int(a.get("change_velocity_30d") or 0), str(n))
                for n, a in self.kg.module_graph.nodes(data=True)
            ],
            reverse=True,
        )[:20]

        citations: List[Citation] = []
        evidence_lines: List[str] = []
        budget = ContextWindowBudget(token_budget=int(config.semanticist.context_budget_tokens))

        for pr, vel, rel in top_mods[:12]:
            fp = (repo_root / rel).resolve()
            if not fp.exists():
                continue
            lr, snip = self._read_lines_with_numbers(fp, 1, 80)
            c = Citation(file=rel, line_range=lr, snippet=snip)
            citations.append(c)
            txt = f"{rel} (pagerank={pr:.6f}, velocity_30d={vel})\n{snip}"
            budget.try_add(title=f"Module Evidence: {rel}", text=txt, citations=[c])

        # Lineage summary evidence.
        try:
            from agents.hydrologist import Hydrologist

            hyd = Hydrologist(self.kg)
            sources = hyd.find_sources()[:30]
            sinks = hyd.find_sinks()[:30]
        except Exception:
            sources, sinks = [], []
        budget.try_add(title="Lineage Sources", text="\n".join(sources) or "(none)")
        budget.try_add(title="Lineage Sinks", text="\n".join(sinks) or "(none)")

        sys_msg = (
            "You are an FDE onboarding assistant. Answer the 5 Day-One questions for this repository. "
            "Use ONLY the provided evidence. For each answer, include 2-5 citations as file:line_range strings. "
            "Output strict JSON only."
        )
        user_msg = (
            f"REPO_ROOT: {repo_root}\n\n"
            f"EVIDENCE:\n{budget.render()}\n\n"
            "Return JSON with keys:\n"
            "- q1_primary_ingestion_path: {answer: string, citations: [string]}\n"
            "- q2_critical_outputs: {answer: string, citations: [string]}\n"
            "- q3_blast_radius: {answer: string, citations: [string]}\n"
            "- q4_business_logic: {answer: string, citations: [string]}\n"
            "- q5_change_velocity: {answer: string, citations: [string]}\n"
        )

        try:
            budget2 = LLMBudget(max_total_tokens=int(config.llm.max_total_tokens))
            model = budget2.choose_model(config=config, task="day_one")
            out = llm_client.chat_completions(
                model=model,
                messages=[ChatMessage(role="system", content=sys_msg), ChatMessage(role="user", content=user_msg)],
                temperature=config.llm.temperature,
                max_tokens=int(config.llm.max_tokens),
                response_format={"type": "json_object"},
            )
            import json as _json

            parsed = _json.loads(out)
            if isinstance(parsed, dict):
                self.kg.module_graph.graph["day_one_answers"] = parsed
                if trace is not None:
                    trace.append(
                        {
                            "ts": self._utc_now(),
                            "agent": "semanticist",
                            "action": "day_one_answers",
                            "method": "llm",
                            "confidence": 0.5,
                            "model": model,
                        }
                    )
        except Exception:
            # Deterministic fallback: keep empty if LLM unavailable.
            self.kg.module_graph.graph["day_one_answers"] = {
                "error": "LLM unavailable for day-one answers. Start LM Studio server and re-run semanticist.",
            }

    def run(
        self,
        repo_root: Path,
        config: CartographyConfig | None = None,
        trace: list[dict] | None = None,
        output_dir: Path | None = None,
    ) -> None:
        """
        Full semanticist phase.
        """
        config = config or CartographyConfig()
        self.annotate_modules(repo_root, config=config, trace=trace, output_dir=output_dir)
        if config.semanticist.day_one_answers:
            self.answer_day_one_questions(repo_root, config=config, trace=trace)
