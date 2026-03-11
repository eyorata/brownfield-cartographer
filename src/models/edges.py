from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

class ImportsEdge(BaseModel):
    source_module: str
    target_module: str
    weight: int = 1
    edge_type: Literal["imports"] = "imports"
    source_file: Optional[str] = None
    line_range: Optional[str] = None

class ProducesEdge(BaseModel):
    transformation: str
    dataset: str
    edge_type: Literal["produces"] = "produces"
    transformation_type: Optional[str] = None
    source_file: Optional[str] = None
    line_range: Optional[str] = None

class ConsumesEdge(BaseModel):
    transformation: str
    dataset: str
    edge_type: Literal["consumes"] = "consumes"
    transformation_type: Optional[str] = None
    source_file: Optional[str] = None
    line_range: Optional[str] = None

class CallsEdge(BaseModel):
    source_function: str
    target_function: str
    edge_type: Literal["calls"] = "calls"
    source_file: Optional[str] = None
    line_range: Optional[str] = None

class ConfiguresEdge(BaseModel):
    config_file: str
    target: str
    edge_type: Literal["configures"] = "configures"
    source_file: Optional[str] = None
    line_range: Optional[str] = None
