from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    base_url: str = Field(default="http://localhost:1234/v1")
    api_key: str = Field(default="lm-studio")
    model: str = Field(default="local-model")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=900, ge=1, le=8192)
    timeout_s: int = Field(default=90, ge=1, le=600)


class SemanticistConfig(BaseModel):
    enabled: bool = True
    max_llm_modules: int = Field(default=120, ge=1, le=5000)
    doc_drift_detection: bool = True
    day_one_answers: bool = True
    context_budget_tokens: int = Field(default=6000, ge=256, le=200000)


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

