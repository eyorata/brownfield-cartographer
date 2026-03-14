from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from llm import OpenAICompatClient


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
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


def _hash_embed(text: str, dim: int = 192) -> List[float]:
    """
    Deterministic fallback embedding (no external model needed).
    Not semantically perfect, but enables vector search + clustering in offline mode.
    """
    vec = [0.0] * dim
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]{1,40}", (text or "").lower())
    if not tokens:
        return vec
    for tok in tokens:
        h = hash(tok)
        idx = abs(h) % dim
        vec[idx] += 1.0
    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def embed_texts(
    texts: List[str],
    *,
    client: Optional[OpenAICompatClient] = None,
    model: str = "local-model",
) -> List[List[float]]:
    if client is not None:
        try:
            if client.is_available(timeout_s=3):
                return client.embeddings(model=model, inputs=texts)
        except Exception:
            pass
    return [_hash_embed(t) for t in texts]


@dataclass(frozen=True)
class SemanticIndexEntry:
    id: str
    kind: str
    module_path: str
    embedding: List[float]
    text: str
    symbol_name: str = ""
    line_range: str = "1-1"


class SemanticIndex:
    def __init__(
        self,
        entries: List[SemanticIndexEntry],
        *,
        embedding_kind: str = "hash_embedding",
        embedding_model: str = "local-model",
    ):
        self.entries = entries
        self.embedding_kind = embedding_kind
        self.embedding_model = embedding_model

    @classmethod
    def build(
        cls,
        *,
        module_texts: List[Tuple[str, str]],
        client: Optional[OpenAICompatClient] = None,
        model: str = "local-model",
    ) -> "SemanticIndex":
        paths = [p for p, _ in module_texts]
        texts = [t for _, t in module_texts]
        embs = embed_texts(texts, client=client, model=model)
        entries: List[SemanticIndexEntry] = []
        for p, e, t in zip(paths, embs, texts, strict=False):
            p = str(p)
            entries.append(
                SemanticIndexEntry(
                    id=f"module:{p}",
                    kind="module",
                    module_path=p,
                    symbol_name="",
                    line_range="1-1",
                    embedding=list(e),
                    text=str(t),
                )
            )
        kind = "embedding" if client is not None else "hash_embedding"
        return cls(entries=entries, embedding_kind=kind, embedding_model=model)

    def search(self, query: str, top_k: int = 25, *, client: Optional[OpenAICompatClient] = None) -> List[Dict[str, Any]]:
        q_emb = embed_texts([query], client=client if self.embedding_kind == "embedding" else None, model=self.embedding_model)[0]
        scored = []
        for ent in self.entries:
            scored.append((_cosine_similarity(q_emb, ent.embedding), ent))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for score, ent in scored[: max(1, int(top_k))]:
            out.append(
                {
                    "id": ent.id,
                    "kind": ent.kind,
                    "module": ent.module_path,
                    "symbol": ent.symbol_name,
                    "line_range": ent.line_range,
                    "score": float(score),
                }
            )
        return out

    def to_json(self) -> Dict[str, Any]:
        dim = len(self.entries[0].embedding) if self.entries and self.entries[0].embedding else 0
        return {
            "version": 2,
            "embedding_kind": self.embedding_kind,
            "embedding_model": self.embedding_model,
            "embedding_dim": dim,
            "entries": [
                {
                    "id": e.id,
                    "kind": e.kind,
                    "module_path": e.module_path,
                    "symbol_name": e.symbol_name,
                    "line_range": e.line_range,
                    "embedding": e.embedding,
                    "text": e.text[:2000],
                }
                for e in self.entries
            ],
        }

    def as_map(self) -> Dict[str, SemanticIndexEntry]:
        return {e.id: e for e in self.entries}

    def updated(
        self,
        *,
        module_texts: List[Tuple[str, str]],
        all_module_paths: Optional[Iterable[str]] = None,
        client: Optional[OpenAICompatClient] = None,
    ) -> "SemanticIndex":
        """
        Incremental update: recompute embeddings for provided module_texts and keep the rest.
        If all_module_paths is provided, drop entries not present in that set.
        """
        existing = self.as_map()
        ids = [p for p, _ in module_texts]
        texts = [t for _, t in module_texts]
        embs = embed_texts(
            texts,
            client=client if self.embedding_kind == "embedding" else None,
            model=self.embedding_model,
        )
        for i, e, t in zip(ids, embs, texts, strict=False):
            i = str(i)
            prev = existing.get(i)
            if prev is None:
                mp = ""
                if i.startswith("module:"):
                    mp = i.split("module:", 1)[1]
                prev = SemanticIndexEntry(
                    id=i,
                    kind="module",
                    module_path=mp,
                    symbol_name="",
                    line_range="1-1",
                    embedding=list(e),
                    text=str(t),
                )
            existing[i] = SemanticIndexEntry(
                id=prev.id,
                kind=prev.kind,
                module_path=prev.module_path,
                symbol_name=prev.symbol_name,
                line_range=prev.line_range,
                embedding=list(e),
                text=str(t),
            )

        if all_module_paths is not None:
            allowed = {str(x) for x in all_module_paths}
            for k, v in list(existing.items()):
                if v.module_path and v.module_path not in allowed:
                    existing.pop(k, None)

        entries = list(existing.values())
        entries.sort(key=lambda x: x.id)
        return SemanticIndex(entries=entries, embedding_kind=self.embedding_kind, embedding_model=self.embedding_model)

    @staticmethod
    def make_entry_id(*, kind: str, module_path: str, symbol_name: str = "", line_range: str = "1-1") -> str:
        kind = str(kind or "module")
        module_path = str(module_path or "")
        symbol_name = str(symbol_name or "")
        line_range = str(line_range or "1-1")
        if kind == "module":
            return f"module:{module_path}"
        return f"{kind}:{module_path}:{symbol_name}:{line_range}"

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "SemanticIndex":
        kind = str(data.get("embedding_kind") or "hash_embedding")
        model = str(data.get("embedding_model") or "local-model")
        version = int(data.get("version") or 1)
        entries = []
        for item in data.get("entries") or []:
            if version <= 1:
                mp = str(item.get("module_path") or "")
                entry_id = f"module:{mp}"
                entry_kind = "module"
                symbol_name = ""
                line_range = "1-1"
            else:
                mp = str(item.get("module_path") or "")
                entry_id = str(item.get("id") or "")
                entry_kind = str(item.get("kind") or "module")
                symbol_name = str(item.get("symbol_name") or "")
                line_range = str(item.get("line_range") or "1-1")
            emb = item.get("embedding") or []
            txt = str(item.get("text") or "")
            if not mp or not isinstance(emb, list):
                continue
            try:
                emb_f = [float(x) for x in emb]
            except Exception:
                continue
            if not entry_id:
                entry_id = f"{entry_kind}:{mp}:{symbol_name}:{line_range}"
            entries.append(
                SemanticIndexEntry(
                    id=entry_id,
                    kind=entry_kind,
                    module_path=mp,
                    symbol_name=symbol_name,
                    line_range=line_range,
                    embedding=emb_f,
                    text=txt,
                )
            )
        return cls(entries=entries, embedding_kind=kind, embedding_model=model)

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_json(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> Optional["SemanticIndex"]:
        p = Path(path)
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return None
            return cls.from_json(data)
        except Exception:
            return None
