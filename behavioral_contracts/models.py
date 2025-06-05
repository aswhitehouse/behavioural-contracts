from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

class TemperatureControl(BaseModel):
    mode: str = Field(..., description="Temperature control mode (fixed/adaptive/dynamic)")
    range: List[float] = Field(..., description="Temperature range [min, max]")

    @field_validator('range')
    def validate_range(cls, v):
        if len(v) != 2:
            raise ValueError("Range must contain exactly 2 values [min, max]")
        if v[0] > v[1]:
            raise ValueError("Range min must be less than max")
        return v

class OnFailure(BaseModel):
    action: str = Field(..., description="Action to take on failure (resubmit_prompt/fallback)")
    max_retries: int = Field(..., description="Maximum number of retries")
    fallback: Dict[str, Any] = Field(..., description="Fallback response")

class OutputFormat(BaseModel):
    type: str = Field(default="object", description="Output format type")
    required_fields: List[str] = Field(..., description="Required fields in response")
    on_failure: OnFailure = Field(..., description="Failure handling configuration")

class ResponseContract(BaseModel):
    output_format: OutputFormat
    max_response_time_ms: int = Field(..., description="Maximum response time in milliseconds")

class Policy(BaseModel):
    PII: bool = Field(..., description="Whether PII is allowed")
    compliance_tags: List[str] = Field(..., description="Required compliance tags")
    allowed_tools: List[str] = Field(..., description="List of allowed tools")

class BehavioralFlags(BaseModel):
    conservatism: str = Field(..., description="Level of conservatism (low/moderate/high)")
    verbosity: str = Field(..., description="Level of verbosity (compact/verbose)")
    temperature_control: TemperatureControl

class Health(BaseModel):
    strikes: int = Field(default=0, description="Number of strikes")
    status: str = Field(default="healthy", description="Health status")

class Escalation(BaseModel):
    on_unexpected_output: str = Field(..., description="Action on unexpected output")
    on_context_mismatch: str = Field(..., description="Action on context mismatch")
    fallback_role: str = Field(..., description="Fallback role to use")

class BehavioralContractSpec(BaseModel):
    version: str
    description: str
    role: str
    policy: Policy
    behavioral_flags: BehavioralFlags
    response_contract: ResponseContract
    health: Health
    escalation: Escalation 