from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

class ModuleNode(BaseModel):
    path: str
    language: str
    purpose_statement: Optional[str] = None
    domain_cluster: Optional[str] = None
    # Documentation drift: heuristics/LLM can populate these.
    doc_drift_score: Optional[float] = None
    doc_drift_flags: Optional[List[str]] = None
    complexity_score: Optional[int] = None
    change_velocity_30d: Optional[int] = None
    is_dead_code_candidate: bool = False
    last_modified: Optional[str] = None
    pagerank: Optional[float] = None
    public_symbol_count: Optional[int] = None
    import_in_degree: Optional[int] = None
    import_out_degree: Optional[int] = None

    @field_validator("path")
    @classmethod
    def _normalize_path(cls, value: str) -> str:
        return value.replace("\\", "/")

    @field_validator("change_velocity_30d")
    @classmethod
    def _non_negative_velocity(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        return max(0, value)

class DatasetNode(BaseModel):
    name: str
    storage_type: Literal["table", "file", "stream", "api"] = "table"
    schema_snapshot: Optional[str] = None
    freshness_sla: Optional[str] = None
    owner: Optional[str] = None
    is_source_of_truth: bool = False

class FunctionNode(BaseModel):
    qualified_name: str
    parent_module: str
    signature: str
    purpose_statement: Optional[str] = None
    call_count_within_repo: int = 0
    is_public_api: bool = False

class TransformationNode(BaseModel):
    source_datasets: List[str]
    target_datasets: List[str]
    transformation_type: str
    source_file: str
    line_range: str = "1-1"
    sql_query_if_applicable: Optional[str] = None

    @field_validator("source_file")
    @classmethod
    def _normalize_source_file(cls, value: str) -> str:
        return value.replace("\\", "/")
