import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
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
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        ]
        self.start_time = None

    def start_timer(self):
        self.start_time = time.time()

    def validate(self, response: Dict[str, Any], policy: Dict[str, Any], behavioral_flags: Dict[str, Any], response_contract: Dict[str, Any], context: Dict[str, Any] = None) -> Tuple[bool, str]:

        for field in self.required_fields:
            if field not in response:
                return False, 'missing required fields'

        if not policy.get('PII', False):
            if self._contains_pii(response):
                return False, 'pii detected in response'

        if 'compliance_tags' in policy:
            if 'compliance_tags' not in response:
                return False, 'missing compliance tags'

        if 'allowed_tools' in policy:
            if 'tools' in response:
                for tool in response['tools']:
                    if tool not in policy['allowed_tools']:
                        return False, 'unauthorized tool used'

        if 'previous_decision' in response:
            if response['previous_decision'] != response['decision']:
                return False, 'high confidence decision changed'

        if 'temperature_used' in response:
            if not (behavioral_flags['temperature_control']['range'][0] <= response['temperature_used'] <= behavioral_flags['temperature_control']['range'][1]):
                return False, 'temperature out of range'

        if self.start_time:
            response_time = (time.time() - self.start_time) * 1000
            if response_time > response_contract.get('max_response_time_ms', 5000):
                return False, 'response time exceeded'

        return True, ''

    def get_fallback_response(self, reason: str) -> Dict[str, Any]:
        fallback = {
            "decision": "unknown",
            "confidence": "low",
            "summary": "Fallback due to error",
            "reasoning": reason
        }
        if 'high confidence decision changed' in reason:
            fallback['flagged_for_review'] = True
        return fallback

    def should_resubmit(self, response: Dict[str, Any], context: Dict[str, Any] = None) -> bool:
        return False

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

    def _high_confidence_change(self, response: Dict[str, Any], context: Dict[str, Any]) -> bool:
        memory = context.get('memory', [])
        if not memory:
            return False
        latest_memory = memory[0].get('analysis', {})
        prev_decision = latest_memory.get('decision', '').lower()
        prev_conf = latest_memory.get('confidence', '').lower()
        current_decision = response.get('decision', '').lower()
        current_conf = response.get('confidence', '').lower()
        if prev_conf == 'high' and prev_decision and current_decision and prev_decision != current_decision and current_conf == 'high':
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