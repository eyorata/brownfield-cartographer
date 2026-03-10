from pydantic import BaseModel

class ImportsEdge(BaseModel):
    source_module: str
    target_module: str
    weight: int = 1

class ProducesEdge(BaseModel):
    transformation: str
    dataset: str

class ConsumesEdge(BaseModel):
    transformation: str
    dataset: str

class CallsEdge(BaseModel):
    source_function: str
    target_function: str

class ConfiguresEdge(BaseModel):
    config_file: str
    target: str
