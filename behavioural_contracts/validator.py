import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from .models import Policy, BehaviouralFlags, ResponseContract
from .exceptions import BehaviouralContractViolation

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

    def validate(self, response: Dict[str, Any], policy: Dict[str, Any], behavioural_flags: Dict[str, Any], response_contract: Dict[str, Any], context: Dict[str, Any] = None) -> Tuple[bool, str]:

        for field in self.required_fields:
            if field not in response:
                return False, 'missing required fields'

        if not policy.get('pii', False):
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
            if not (behavioural_flags['temperature_control']['range'][0] <= response['temperature_used'] <= behavioural_flags['temperature_control']['range'][1]):
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

class BehaviouralFlags(BaseModel):
    conservatism: str = Field(..., description="Level of conservatism (low/moderate/high)")
    verbosity: str = Field(..., description="Level of verbosity (compact/verbose)")
    temperature_control: TemperatureControl

class FallbackResponse(BaseModel):
    recommendation: str
    confidence: str
    summary: str
    reasoning: str

class BehaviouralContract(BaseModel):
    version: str
    description: str
    role: str
    policy: Policy
    behavioural_flags: BehaviouralFlags
    response_contract: ResponseContract
    health: Dict[str, Any]
    escalation: Dict[str, Any]

def validate_contract(contract: BehaviouralContract) -> None:
    """Validate a behavioural contract.
    
    Args:
        contract: The contract to validate
        
    Raises:
        BehaviouralContractViolation: If the contract is invalid
    """
    # Validate version
    if not contract.version:
        raise BehaviouralContractViolation("Contract version is required")
        
    # Validate description
    if not contract.description:
        raise BehaviouralContractViolation("Contract description is required")
        
    # Validate role
    if not contract.role:
        raise BehaviouralContractViolation("Contract role is required")
        
    # Validate policy
    if not contract.policy.get('compliance_tags'):
        raise BehaviouralContractViolation("At least one compliance tag is required")
    if not contract.policy.get('allowed_tools'):
        raise BehaviouralContractViolation("At least one allowed tool is required")
        
    # Validate behavioural flags
    if not contract.behavioural_flags.get('conservatism'):
        raise BehaviouralContractViolation("Conservatism level is required")
    if not contract.behavioural_flags.get('verbosity'):
        raise BehaviouralContractViolation("Verbosity level is required")

def validate_response(response: dict, contract: dict, policy: dict, behavioural_flags: dict = None) -> None:
    """Validate a response against the contract requirements."""
    logger.info(f"Validating response: {response}")
    logger.info(f"Against contract: {contract}")
    logger.info(f"Using policy: {policy}")
    if behavioural_flags is not None:
        logger.info(f"Using behavioural_flags: {behavioural_flags}")
    
    # Check required fields
    required_fields = contract["required_fields"]
    logger.info(f"Required fields: {required_fields}")
    
    for field in required_fields:
        if field not in response:
            logger.warning(f"Missing required field: {field}")
            raise BehaviouralContractViolation(f"Missing required field: {field}")
        logger.info(f"Field {field} present with value: {response[field]}")

    # Check PII if not allowed
    if not policy.get("pii", False):
        if contains_pii(response):
            logger.warning("PII detected in response")
            raise BehaviouralContractViolation("Response contains PII which is not allowed")

    # Check compliance tags
    if "compliance_tags" in required_fields:
        required_tags = policy.get("compliance_tags", [])
        if "compliance_tags" not in response or not response["compliance_tags"]:
            logger.warning("Missing required compliance tags")
            raise BehaviouralContractViolation("Missing required compliance tags")
        for tag in required_tags:
            if tag not in response["compliance_tags"]:
                logger.warning(f"Missing required compliance tag: {tag}")
                raise BehaviouralContractViolation(f"Missing required compliance tag: {tag}")

    # Check allowed tools
    if "tools" in response:
        allowed_tools = policy.get("allowed_tools", [])
        unauthorized = [tool for tool in response["tools"] if tool not in allowed_tools]
        if unauthorized:
            logger.warning(f"Unauthorized tools used: {unauthorized}")
            raise BehaviouralContractViolation(f"Unauthorized tools used: {', '.join(unauthorized)}")

    # Check temperature control
    if "temperature_used" in required_fields:
        if "temperature_used" not in response:
            logger.warning("Missing required temperature_used field")
            raise BehaviouralContractViolation("Missing required temperature_used field")
        temp = response["temperature_used"]
        if not isinstance(temp, (int, float)):
            logger.warning(f"Temperature must be a number, got {type(temp)}")
            raise BehaviouralContractViolation("Temperature must be a number")
        # Use behavioural_flags for temperature range if provided
        min_temp, max_temp = 0.0, 1.0
        if behavioural_flags and "temperature_control" in behavioural_flags:
            temp_control = behavioural_flags["temperature_control"]
            if "range" in temp_control and isinstance(temp_control["range"], list) and len(temp_control["range"]) == 2:
                min_temp, max_temp = temp_control["range"]
        if not min_temp <= temp <= max_temp:
            logger.warning(f"Temperature {temp} outside allowed range [{min_temp}, {max_temp}]")
            raise BehaviouralContractViolation(f"Temperature {temp} outside allowed range [{min_temp}, {max_temp}]")

    # Check confidence levels
    if "confidence" in response:
        allowed_levels = contract.get("confidence_levels", ["low", "medium", "high"])
        if response["confidence"] not in allowed_levels:
            logger.warning(f"Invalid confidence level: {response['confidence']}")
            raise BehaviouralContractViolation(f"Invalid confidence level: {response['confidence']}")

    # Check decision values
    if "decision" in response:
        allowed_decisions = contract.get("allowed_decisions", [])
        if allowed_decisions and response["decision"] not in allowed_decisions:
            logger.warning(f"Invalid decision: {response['decision']}")
            raise BehaviouralContractViolation(f"Invalid decision: {response['decision']}")

    logger.info("Response validation passed all checks")

def contains_pii(response: dict) -> bool:
    """Check if response contains PII."""
    # Simple PII detection - can be enhanced with more sophisticated checks
    pii_patterns = [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone
        r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b',  # SSN
    ]
    
    for value in response.values():
        if isinstance(value, str):
            for pattern in pii_patterns:
                if re.search(pattern, value):
                    return True
    return False