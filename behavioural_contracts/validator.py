import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from .exceptions import BehaviouralContractViolationError
from .models import BehaviouralFlags, Policy, ResponseContract

logger = logging.getLogger(__name__)


def try_parse_json(raw_content: Any) -> Optional[Dict[Any, Any]]:
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
                return dict(json.loads(content))
            except json.JSONDecodeError:
                return None

    try:
        return dict(json.loads(raw_content))
    except json.JSONDecodeError:
        return None


class TemperatureControl(BaseModel):
    mode: str = Field(..., description="Temperature control mode (fixed/adaptive)")
    range: List[float] = Field(..., description="Temperature range [min, max]")


class OutputFormat(BaseModel):
    type: str = Field(default="object", description="Output format type")
    required_fields: List[str] = Field(..., description="Required fields in response")
    on_failure: Dict[str, Any] = Field(
        ..., description="Failure handling configuration"
    )


class ResponseValidator:
    def __init__(self, required_fields: List[str]):
        self.required_fields = required_fields
        self.pii_patterns = [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        ]
        self.start_time: Optional[float] = None

    def start_timer(self) -> float:
        self.start_time = time.time()
        return self.start_time

    def _validate_required_fields(self, response: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate that all required fields are present in the response."""
        for field in self.required_fields:
            if field not in response:
                return False, "missing required fields"
        return True, ""

    def _validate_pii(
        self, response: Dict[str, Any], policy: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Validate PII restrictions."""
        if not policy.get("pii", False) and self._contains_pii(response):
            return False, "pii detected in response"
        return True, ""

    def _validate_compliance(
        self,
        response: Dict[str, Any],
        policy: Dict[str, Any],
        required_fields: Optional[list] = None,
    ) -> Tuple[bool, str]:
        """Validate compliance tags."""
        if required_fields is not None and "compliance_tags" not in required_fields:
            return True, ""
        if "compliance_tags" in policy and policy.get("compliance_tags"):
            if "compliance_tags" not in response:
                return False, "missing compliance tags"
            if not all(
                tag in policy["compliance_tags"] for tag in response["compliance_tags"]
            ):
                return False, "invalid compliance tags"
        return True, ""

    def _validate_tools(
        self, response: Dict[str, Any], policy: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Validate tool usage."""
        if "allowed_tools" in policy and "tools" in response:
            for tool in response["tools"]:
                if tool not in policy["allowed_tools"]:
                    return False, "unauthorized tool used"
        return True, ""

    def _validate_decision_change(self, response: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate decision changes."""
        if (
            "previous_decision" in response
            and response["previous_decision"] != response["decision"]
        ):
            return False, "high confidence decision changed"
        return True, ""

    def _validate_temperature_range(
        self, response: Dict[str, Any], behavioural_flags: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Validate temperature range."""
        if "temperature_used" in response:
            temp_range = behavioural_flags["temperature_control"]["range"]
            if not (temp_range[0] <= response["temperature_used"] <= temp_range[1]):
                return False, "temperature out of range"
        return True, ""

    def _validate_response_time(
        self, response_contract: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Validate response time."""
        if self.start_time:
            response_time = (time.time() - self.start_time) * 1000
            if response_time > response_contract.get("max_response_time_ms", 5000):
                return False, "response time exceeded"
        return True, ""

    def validate(
        self,
        response: Dict[str, Any],
        policy: Dict[str, Any],
        behavioural_flags: Dict[str, Any],
        response_contract: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """Validate a response against all requirements.

        Args:
            response: The response to validate
            policy: Policy configuration
            behavioural_flags: Behavioural flags configuration
            response_contract: Response contract configuration

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate required fields
        is_valid, error = self._validate_required_fields(response)
        if not is_valid:
            return False, error

        # Validate PII
        is_valid, error = self._validate_pii(response, policy)
        if not is_valid:
            return False, error

        # Validate compliance
        is_valid, error = self._validate_compliance(
            response, policy, self.required_fields
        )
        if not is_valid:
            return False, error

        # Validate tools
        is_valid, error = self._validate_tools(response, policy)
        if not is_valid:
            return False, error

        # Validate decision changes
        is_valid, error = self._validate_decision_change(response)
        if not is_valid:
            return False, error

        # Validate temperature range
        is_valid, error = self._validate_temperature_range(response, behavioural_flags)
        if not is_valid:
            return False, error

        # Validate response time
        is_valid, error = self._validate_response_time(response_contract)
        if not is_valid:
            return False, error

        return True, ""

    def get_fallback_response(self, reason: str) -> Dict[str, Any]:
        """Get a fallback response when validation fails.

        Args:
            reason: The reason for the fallback

        Returns:
            A dictionary containing the fallback response
        """
        fallback: Dict[str, Any] = {
            "decision": "unknown",
            "confidence": "low",
            "summary": "Fallback due to error",
            "reasoning": reason,
        }
        if "high confidence decision changed" in reason:
            fallback["flagged_for_review"] = True
        return fallback

    def should_resubmit(self) -> bool:
        return False

    def _contains_pii(self, response: Dict[str, Any]) -> bool:
        """Check if response contains any PII."""
        text = str(response)
        return any(re.search(pattern, text) for pattern in self.pii_patterns)

    def _validate_compliance_tags(
        self, response: Dict[str, Any], required_tags: List[str]
    ) -> bool:
        """Validate that all required compliance tags are present."""
        if "compliance_tags" not in response:
            return False
        return all(tag in response["compliance_tags"] for tag in required_tags)

    def _validate_allowed_tools(
        self, response: Dict[str, Any], allowed_tools: List[str]
    ) -> bool:
        """Validate that only allowed tools are used."""
        if "tools" not in response:
            return True  # No tools used is valid
        return all(tool in allowed_tools for tool in response["tools"])

    def _validate_temperature(
        self, temperature: float, control: Dict[str, Any]
    ) -> bool:
        """Validate that temperature is within allowed range."""
        min_temp = getattr(control, "min", 0.2)
        max_temp = getattr(control, "max", 0.6)
        return min_temp <= temperature <= max_temp

    def _high_confidence_change(
        self, response: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        memory = context.get("memory", [])
        if not memory:
            return False
        latest_memory = memory[0].get("analysis", {})
        prev_decision = latest_memory.get("decision", "").lower()
        prev_conf = latest_memory.get("confidence", "").lower()
        current_decision = response.get("decision", "").lower()
        current_conf = response.get("confidence", "").lower()
        if (
            prev_conf == "high"
            and prev_decision != current_decision
            and current_conf == "high"
        ):
            return True
        return False


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
        raise BehaviouralContractViolationError("Contract version is required")

    # Validate description
    if not contract.description:
        raise BehaviouralContractViolationError("Contract description is required")

    # Validate role
    if not contract.role:
        raise BehaviouralContractViolationError("Contract role is required")

    # Validate policy
    if not contract.policy.compliance_tags:
        raise BehaviouralContractViolationError(
            "At least one compliance tag is required"
        )
    if not contract.policy.allowed_tools:
        raise BehaviouralContractViolationError("At least one allowed tool is required")

    # Validate behavioural flags
    if not contract.behavioural_flags.conservatism:
        raise BehaviouralContractViolationError("Conservatism level is required")
    if not contract.behavioural_flags.verbosity:
        raise BehaviouralContractViolationError("Verbosity level is required")


def _validate_required_fields_in_response(
    response: dict, required_fields: List[str]
) -> None:
    """Validate that all required fields are present in the response.

    Args:
        response: The response to validate
        required_fields: List of required field names

    Raises:
        BehaviouralContractViolationError: If any required field is missing
    """
    for field in required_fields:
        if field not in response:
            logger.warning(f"Missing required field: {field}")
            raise BehaviouralContractViolationError(f"Missing required field: {field}")
        logger.info(f"Field {field} present with value: {response[field]}")


def _validate_pii_in_response(response: dict, policy: dict) -> None:
    """Validate that no PII is present if not allowed by policy.

    Args:
        response: The response to validate
        policy: The policy configuration

    Raises:
        BehaviouralContractViolationError: If PII is detected and not allowed
    """
    if not policy.get("pii", False) and contains_pii(response):
        logger.warning("PII detected in response")
        raise BehaviouralContractViolationError(
            "Response contains PII which is not allowed"
        )


def _validate_compliance_tags_in_response(response: dict, policy: dict) -> None:
    """Validate that all required compliance tags are present.

    Args:
        response: The response to validate
        policy: The policy configuration

    Raises:
        BehaviouralContractViolationError: If required tags are missing
    """
    required_tags = policy.get("compliance_tags", [])
    if "compliance_tags" not in response or not response["compliance_tags"]:
        logger.warning("Missing required compliance tags")
        raise BehaviouralContractViolationError("Missing required compliance tags")
    for tag in required_tags:
        if tag not in response["compliance_tags"]:
            logger.warning(f"Missing required compliance tag: {tag}")
            raise BehaviouralContractViolationError(
                f"Missing required compliance tag: {tag}"
            )


def _validate_tools_in_response(response: dict, policy: dict) -> None:
    """Validate that only allowed tools are used.

    Args:
        response: The response to validate
        policy: The policy configuration

    Raises:
        BehaviouralContractViolationError: If unauthorized tools are used
    """
    if "tools" in response:
        allowed_tools = policy.get("allowed_tools", [])
        unauthorized = [tool for tool in response["tools"] if tool not in allowed_tools]
        if unauthorized:
            logger.warning(f"Unauthorized tools used: {unauthorized}")
            raise BehaviouralContractViolationError(
                f"Unauthorized tools used: {', '.join(unauthorized)}"
            )


def _validate_temperature_in_response(
    response: dict, behavioural_flags: Optional[Any]
) -> None:
    """Validate that temperature is within allowed range.

    Args:
        response: The response to validate
        behavioural_flags: Optional behavioural flags configuration

    Raises:
        BehaviouralContractViolationError: If temperature is invalid or out of range
    """
    if "temperature_used" not in response:
        logger.warning("Missing required temperature_used field")
        raise BehaviouralContractViolationError(
            "Missing required temperature_used field"
        )

    temp = response["temperature_used"]
    if not isinstance(temp, (int, float)):
        logger.warning(f"Temperature must be a number, got {type(temp)}")
        raise BehaviouralContractViolationError("Temperature must be a number")

    min_temp, max_temp = 0.0, 1.0
    if behavioural_flags:
        if isinstance(behavioural_flags, dict):
            tc = behavioural_flags.get("temperature_control")
            if tc:
                min_temp, max_temp = tc["range"]
        else:
            tc = getattr(behavioural_flags, "temperature_control", None)
            if tc:
                min_temp, max_temp = tc.range

    if not min_temp <= temp <= max_temp:
        logger.warning(
            f"Temperature {temp} outside allowed range [{min_temp}, {max_temp}]"
        )
        raise BehaviouralContractViolationError(
            f"Temperature {temp} outside allowed range [{min_temp}, {max_temp}]"
        )


def _validate_confidence_in_response(response: dict, contract: dict) -> None:
    """Validate that confidence level is allowed.

    Args:
        response: The response to validate
        contract: The contract configuration

    Raises:
        BehaviouralContractViolationError: If confidence level is invalid
    """
    if "confidence" in response:
        allowed_levels = contract.get("confidence_levels", ["low", "medium", "high"])
        if response["confidence"] not in allowed_levels:
            logger.warning(f"Invalid confidence level: {response['confidence']}")
            raise BehaviouralContractViolationError(
                f"Invalid confidence level: {response['confidence']}"
            )


def _validate_decision_in_response(response: dict, contract: dict) -> None:
    """Validate that decision value is allowed.

    Args:
        response: The response to validate
        contract: The contract configuration

    Raises:
        BehaviouralContractViolationError: If decision value is invalid
    """
    if "decision" in response:
        allowed_decisions = contract.get("allowed_decisions", [])
        if allowed_decisions and response["decision"] not in allowed_decisions:
            logger.warning(f"Invalid decision: {response['decision']}")
            raise BehaviouralContractViolationError(
                f"Invalid decision: {response['decision']}"
            )


def validate_response(
    response: dict,
    contract: dict,
    policy: dict,
    behavioural_flags: Optional[BehaviouralFlags] = None,
) -> None:
    """Validate a response against the contract requirements.

    Args:
        response: The response to validate
        contract: The contract configuration
        policy: The policy configuration
        behavioural_flags: Optional behavioural flags configuration

    Raises:
        BehaviouralContractViolationError: If any validation fails
    """
    logger.info(f"Validating response: {response}")
    logger.info(f"Against contract: {contract}")
    logger.info(f"Using policy: {policy}")
    if behavioural_flags is not None:
        logger.info(f"Using behavioural_flags: {behavioural_flags}")

    required_fields = contract["required_fields"]
    logger.info(f"Required fields: {required_fields}")

    _validate_required_fields_in_response(response, required_fields)
    _validate_pii_in_response(response, policy)

    if "compliance_tags" in required_fields:
        _validate_compliance_tags_in_response(response, policy)

    _validate_tools_in_response(response, policy)

    if "temperature_used" in required_fields:
        _validate_temperature_in_response(response, behavioural_flags)

    _validate_confidence_in_response(response, contract)
    _validate_decision_in_response(response, contract)

    logger.info("Response validation passed all checks")


def contains_pii(response: dict) -> bool:
    """Check if response contains PII."""
    # Simple PII detection - can be enhanced with more sophisticated checks
    pii_patterns = [
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
        r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # Phone
        r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b",  # SSN
    ]

    for value in response.values():
        if isinstance(value, str):
            for pattern in pii_patterns:
                if re.search(pattern, value):
                    return True
    return False
