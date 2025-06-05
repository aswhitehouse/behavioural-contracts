import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .models import Policy, BehavioralFlags, ResponseContract

logger = logging.getLogger(__name__)

def try_parse_json(raw_content: Any) -> Optional[Dict]:
    """Helper function to parse JSON content with various formats."""
    if isinstance(raw_content, dict):
        return raw_content

    if not isinstance(raw_content, str):
        return None

    raw_content = raw_content.strip()

    # Handle markdown code blocks
    if raw_content.startswith("```") and raw_content.endswith("```"):
        content_lines = raw_content.split("\n")
        if len(content_lines) > 2:
            content = "\n".join(content_lines[1:-1])
            content = content.replace("```", "").strip()
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return None

    try:
        return json.loads(raw_content)
    except json.JSONDecodeError:
        return None

class TemperatureControl(BaseModel):
    mode: str = Field(..., description="Temperature control mode (fixed/adaptive)")
    range: List[float] = Field(..., description="Temperature range [min, max]")

class OutputFormat(BaseModel):
    type: str = Field(default="object", description="Output format type")
    required_fields: List[str] = Field(..., description="Required fields in response")
    on_failure: Dict[str, Any] = Field(..., description="Failure handling configuration")

class ResponseValidator:
    def __init__(self, required_fields: List[str]):
        self.required_fields = required_fields
        self.pii_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'   # URL
        ]
        self.start_time = None

    def validate(self, response: Dict[str, Any], policy: Optional[Policy] = None, 
                behavioral_flags: Optional[BehavioralFlags] = None,
                response_contract: Optional[ResponseContract] = None,
                context: Optional[Dict[str, Any]] = None) -> tuple[bool, str]:
        """Validate the response against the contract requirements."""
        try:
            # Check required fields
            if not self._validate_required_fields(response):
                return False, "missing required fields"

            # Check PII if policy is provided
            if policy and not policy.PII:
                if self._contains_pii(response):
                    return False, "PII detected in response"

            # Check compliance tags if policy is provided
            if policy and not self._validate_compliance_tags(response, policy.compliance_tags):
                return False, "missing required compliance tags"

            # Check allowed tools if policy is provided
            if policy and not self._validate_allowed_tools(response, policy.allowed_tools):
                return False, "unauthorized tools used"

            # Check temperature if behavioral flags are provided
            if behavioral_flags and hasattr(behavioral_flags, 'temperature_control') and 'temperature_used' in response:
                tc = behavioral_flags.temperature_control
                if not self._validate_temperature(response['temperature_used'], tc):
                    return False, "temperature outside allowed range"

            # Check response time
            if self.start_time and response_contract and hasattr(response_contract, 'max_response_time_ms'):
                response_time = (time.time() - self.start_time) * 1000
                if response_time > response_contract.max_response_time_ms:
                    return False, "timeout: response time exceeded limit"

            # High confidence change detection
            if context and self._high_confidence_change(response, context):
                return False, "high confidence recommendation changed"

            return True, ""

        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return False, str(e)

    def _validate_required_fields(self, response: Dict[str, Any]) -> bool:
        """Check if all required fields are present."""
        return all(field in response for field in self.required_fields)

    def _contains_pii(self, response: Dict[str, Any]) -> bool:
        """Check if response contains any PII."""
        text = str(response)
        return any(re.search(pattern, text) for pattern in self.pii_patterns)

    def _validate_compliance_tags(self, response: Dict[str, Any], required_tags: List[str]) -> bool:
        """Validate that all required compliance tags are present."""
        if 'compliance_tags' not in response:
            return False
        return all(tag in response['compliance_tags'] for tag in required_tags)

    def _validate_allowed_tools(self, response: Dict[str, Any], allowed_tools: List[str]) -> bool:
        """Validate that only allowed tools are used."""
        if 'tools' not in response:
            return True  # No tools used is valid
        return all(tool in allowed_tools for tool in response['tools'])

    def _validate_temperature(self, temperature: float, control) -> bool:
        """Validate that temperature is within allowed range."""
        min_temp = getattr(control, 'min', 0.2)
        max_temp = getattr(control, 'max', 0.6)
        return min_temp <= temperature <= max_temp

    def should_resubmit(self, response: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if the response should be resubmitted."""
        if not context:
            return False

        # Check for high confidence changes
        if 'previous_recommendation' in response:
            current_rec = response.get('recommendation', '').lower()
            prev_rec = response['previous_recommendation'].lower()
            if current_rec != prev_rec and response.get('confidence', '').lower() == 'high':
                logger.warning("High confidence recommendation changed")
                return True

        return False

    def get_fallback_response(self, reason: str) -> Dict[str, Any]:
        """Get the appropriate fallback response."""
        return {
            "recommendation": "unknown",
            "confidence": "low",
            "summary": "Recommendation rejected due to validation failure.",
            "reasoning": f"The model's recommendation was rejected because {reason}."
        }

    def start_timer(self):
        """Start the response time timer."""
        self.start_time = time.time()

    def _high_confidence_change(self, response: Dict[str, Any], context: Dict[str, Any]) -> bool:
        # Simulate memory with previous high confidence recommendation
        memory = context.get('memory', [])
        if not memory:
            return False
        latest_memory = memory[0].get('analysis', {})
        prev_rec = latest_memory.get('recommendation', '').lower()
        prev_conf = latest_memory.get('confidence', '').lower()
        current_rec = response.get('recommendation', '').lower()
        current_conf = response.get('confidence', '').lower()
        if prev_conf == 'high' and prev_rec and current_rec and prev_rec != current_rec and current_conf == 'high':
            return True
        return False

class BehavioralFlags(BaseModel):
    conservatism: str = Field(..., description="Level of conservatism (low/moderate/high)")
    verbosity: str = Field(..., description="Level of verbosity (compact/verbose)")
    temperature_control: TemperatureControl

class FallbackResponse(BaseModel):
    recommendation: str
    confidence: str
    summary: str
    reasoning: str

class BehavioralContract(BaseModel):
    version: str
    description: str
    role: str
    policy: Policy
    behavioral_flags: BehavioralFlags
    response_contract: ResponseContract
    health: Dict[str, Any]
    escalation: Dict[str, Any]