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
    # Supports environment override via base_url_env. For LM Studio you can set:
    #   LMSTUDIO_API_BASE=http://192.168.6.233:1234/v1
    # and leave base_url_env as "LMSTUDIO_API_BASE".
    base_url: str = Field(default="http://localhost:1234/v1")
    base_url_env: str = Field(default="LMSTUDIO_API_BASE")

    # API key can be set directly or sourced from an env var.
    # Supports env indirection (recommended for secrets):
    #   LMSTUDIO_API_KEY_ENV=LMSTUDIO_API_KEY
    #   LMSTUDIO_API_KEY=... (actual secret value)
    api_key: str = Field(default="")
    api_key_env: str = Field(default="LMSTUDIO_API_KEY_ENV")

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

    @staticmethod
    def _looks_like_env_var_name(value: str) -> bool:
        s = (value or "").strip()
        if not s:
            return False
        if len(s) > 120:
            return False
        if not ("A" <= s[0] <= "Z"):
            return False
        for ch in s:
            if not (("A" <= ch <= "Z") or ("0" <= ch <= "9") or ch == "_"):
                return False
        return True

    def _resolve_env_value(self, env_name: str) -> str:
        """
        Resolve env values with one level of indirection:
        - If env_name points to a value like "SOME_SECRET_ENV" and that env var exists,
          return the value of SOME_SECRET_ENV.
        - Otherwise, return the value of env_name.
        """
        name = (env_name or "").strip()
        if not name:
            return ""
        first = str(os.environ.get(name, "") or "")
        if not first:
            return ""
        candidate = first.strip()
        if (
            self._looks_like_env_var_name(candidate)
            and candidate != name
            and os.environ.get(candidate) is not None
        ):
            return str(os.environ.get(candidate, "") or "")
        return first

    def resolved_base_url(self) -> str:
        env_name = (self.base_url_env or "").strip()
        if env_name:
            v = self._resolve_env_value(env_name)
            if v:
                return str(v).rstrip("/")
        return str(self.base_url).rstrip("/")

    def resolved_api_key(self) -> str:
        if self.api_key:
            return str(self.api_key)
        env_name = (self.api_key_env or "").strip()
        if env_name:
            v = self._resolve_env_value(env_name)
            if v:
                return str(v)

        # Provider-friendly fallbacks.
        if self.provider == "openrouter":
            return str(os.environ.get("OPENROUTER_API_KEY", "") or "")
        if self.provider == "openai_compat":
            return str(os.environ.get("OPENAI_API_KEY", "") or "")
        if self.provider == "lmstudio":
            return str(os.environ.get("LMSTUDIO_API_KEY", "") or "")
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
