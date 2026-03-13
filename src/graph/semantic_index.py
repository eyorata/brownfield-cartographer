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
    module_path: str
    embedding: List[float]
    text: str


class SemanticIndex:
    def __init__(self, entries: List[SemanticIndexEntry], *, embedding_kind: str = "hash_embedding", embedding_model: str = "local-model"):
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
        entries = [
            SemanticIndexEntry(module_path=p, embedding=e, text=t) for p, e, t in zip(paths, embs, texts, strict=False)
        ]
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
            out.append({"module": ent.module_path, "score": float(score)})
        return out

    def to_json(self) -> Dict[str, Any]:
        dim = len(self.entries[0].embedding) if self.entries and self.entries[0].embedding else 0
        return {
            "version": 1,
            "embedding_kind": self.embedding_kind,
            "embedding_model": self.embedding_model,
            "embedding_dim": dim,
            "entries": [
                {"module_path": e.module_path, "embedding": e.embedding, "text": e.text[:2000]} for e in self.entries
            ],
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "SemanticIndex":
        kind = str(data.get("embedding_kind") or "hash_embedding")
        model = str(data.get("embedding_model") or "local-model")
        entries = []
        for item in data.get("entries") or []:
            mp = str(item.get("module_path") or "")
            emb = item.get("embedding") or []
            txt = str(item.get("text") or "")
            if not mp or not isinstance(emb, list):
                continue
            try:
                emb_f = [float(x) for x in emb]
            except Exception:
                continue
            entries.append(SemanticIndexEntry(module_path=mp, embedding=emb_f, text=txt))
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
