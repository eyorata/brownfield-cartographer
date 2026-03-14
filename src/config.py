from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    # Provider is advisory; we still use an OpenAI-compatible API client underneath.
    provider: str = Field(default="lmstudio")  # lmstudio | openrouter | openai_compat | other

    # Base URL of the OpenAI-compatible API (e.g. LM Studio, OpenRouter).
    # Supports environment override via LMSTUDIO_API_BASE or base_url_env.
    base_url: str = Field(default="http://localhost:1234/v1")
    base_url_env: str = Field(default="LMSTUDIO_API_BASE")

    # API key can be set directly or sourced from an env var name.
    api_key: str = Field(default="")
    api_key_env: str = Field(default_factory=lambda: os.environ.get("LMSTUDIO_API_KEY_ENV", ""))

    # Optional OpenRouter-style attribution headers (also useful for other paid gateways).
    app_url: str = Field(default_factory=lambda: os.environ.get("OPENROUTER_APP_URL", ""))
    app_name: str = Field(default_factory=lambda: os.environ.get("OPENROUTER_APP_NAME", ""))

    # Backwards-compatible default model name (used by older configs).
    model: str = Field(default="local-model")
    # Cost-conscious selection: cheap model for bulk, expensive model for synthesis.
    cheap_model: str = Field(default="local-model")
    expensive_model: str = Field(default="local-model")
    # Embeddings model for semantic index / vector search (can differ from chat models).
    embedding_model: str = Field(default="local-model")
    # Optional vision-capable model name (if your server supports images).
    vision_model: str = Field(default_factory=lambda: os.environ.get("LMSTUDIO_VISION_MODEL", ""))
    max_total_tokens: int = Field(default=200_000, ge=1, le=10_000_000)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=900, ge=1, le=8192)
    timeout_s: int = Field(default=90, ge=1, le=600)

    def resolved_base_url(self) -> str:
        env_name = (self.base_url_env or "").strip()
        if env_name:
            v = os.environ.get(env_name)
            if v:
                return str(v).rstrip("/")
        # Back-compat: accept LMSTUDIO_API_BASE directly if present.
        v2 = os.environ.get("LMSTUDIO_API_BASE")
        if v2:
            return str(v2).rstrip("/")
        return str(self.base_url).rstrip("/")

    def resolved_api_key(self) -> str:
        if self.api_key:
            return str(self.api_key)
        env_name = (self.api_key_env or "").strip()
        if env_name:
            return str(os.environ.get(env_name, ""))
        return ""

    def resolved_embedding_model(self) -> str:
        return str(self.embedding_model or self.cheap_model or self.model)

    def extra_headers(self) -> dict[str, str]:
        # OpenRouter recommends sending these; harmless for most other gateways.
        headers: dict[str, str] = {}
        if self.app_url:
            headers["HTTP-Referer"] = str(self.app_url)
        if self.app_name:
            headers["X-Title"] = str(self.app_name)
        return headers


class SemanticistConfig(BaseModel):
    enabled: bool = True
    max_llm_modules: int = Field(default=120, ge=1, le=5000)
    doc_drift_detection: bool = True
    day_one_answers: bool = True
    context_budget_tokens: int = Field(default=6000, ge=256, le=200000)
    # Build and persist a semantic index for Navigator find_implementation().
    semantic_index: bool = True
    # Max modules to embed for the index/clustering.
    max_semantic_index_modules: int = Field(default=2500, ge=10, le=50_000)
    # Include per-function and per-class entries in the semantic index (Python only).
    semantic_index_symbols: bool = True
    # Cap symbols per module to keep index size reasonable.
    max_symbols_per_module: int = Field(default=250, ge=10, le=10_000)


class NavigatorConfig(BaseModel):
    use_langgraph: bool = True
    citations: bool = True


class IncrementalConfig(BaseModel):
    enabled: bool = False
    diff_range: str = "HEAD~1..HEAD"


class CartographyConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    semanticist: SemanticistConfig = Field(default_factory=SemanticistConfig)
    navigator: NavigatorConfig = Field(default_factory=NavigatorConfig)
    incremental: IncrementalConfig = Field(default_factory=IncrementalConfig)


def load_config(path: str | Path | None) -> CartographyConfig:
    """
    Loads YAML config if provided (or if default config file exists).
    Falls back to defaults if config cannot be read.
    """
    if path is None:
        default = Path("cartography_config.yaml")
        if default.exists():
            path = default
        else:
            return CartographyConfig()

    path = Path(path)
    try:
        import yaml  # provided by pyyaml dependency
    except Exception:
        # No YAML parser available; return defaults.
        return CartographyConfig()

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            return CartographyConfig()
        return CartographyConfig.model_validate(raw)
    except Exception:
        return CartographyConfig()
