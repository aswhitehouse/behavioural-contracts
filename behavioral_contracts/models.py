from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field, validator

class TemperatureControl(BaseModel):
    mode: Literal["fixed", "dynamic"] = "fixed"
    range: List[float] = Field(default=[0.2, 0.6], min_items=2, max_items=2)
    
    @validator('range')
    def validate_range(cls, v):
        if v[0] >= v[1]:
            raise ValueError("Temperature range must be in ascending order")
        if not all(0 <= x <= 1 for x in v):
            raise ValueError("Temperature values must be between 0 and 1")
        return v

class BehavioralFlags(BaseModel):
    temperature_control: TemperatureControl = Field(default_factory=TemperatureControl)

class FallbackResponse(BaseModel):
    action: str
    confidence: str
    reason: str = "Fallback due to error"

class OutputFormat(BaseModel):
    required_fields: List[str]
    max_response_time_ms: int = 5000
    max_retries: int = 1
    on_failure: Dict[str, FallbackResponse]

class ResponseContract(BaseModel):
    output_format: OutputFormat

class HealthConfig(BaseModel):
    max_strikes: int = 3
    strike_window_seconds: int = 3600

class EscalationConfig(BaseModel):
    on_unexpected_output: Literal["flag_for_review", "fallback"] = "flag_for_review"
    on_invalid_response: Literal["flag_for_review", "fallback"] = "fallback"

class BehavioralContractSpec(BaseModel):
    version: str = "1.0"
    description: str = ""
    role: str = "default"
    behavioral_flags: BehavioralFlags = Field(default_factory=BehavioralFlags)
    response_contract: ResponseContract
    health: HealthConfig = Field(default_factory=HealthConfig)
    escalation: EscalationConfig = Field(default_factory=EscalationConfig)

    class Config:
        extra = "forbid"  # Prevent additional fields 