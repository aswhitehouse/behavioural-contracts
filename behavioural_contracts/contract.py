import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from .exceptions import BehaviouralContractViolationError
from .health_monitor import HealthMonitor
from .temperature import TemperatureController
from .validator import ResponseValidator

logger = logging.getLogger(__name__)


class BehaviouralContract:
    def __init__(self, contract_spec: Dict[str, Any]) -> None:
        self.version = contract_spec.get("version", "1.0")
        self.description = contract_spec.get("description", "")
        self.role = contract_spec.get("role", "default")
        self.policy = contract_spec.get("policy", {})
        self.behavioural_flags = contract_spec.get("behavioural_flags", {})
        self.response_contract = contract_spec.get("response_contract", {})
        self.health = contract_spec.get("health", {})
        self.escalation = contract_spec.get("escalation", {})

        # Initialize components
        self.health_monitor = HealthMonitor()
        self.temp_controller = TemperatureController(
            self.behavioural_flags.get("temperature_control", {}).get("mode", "fixed"),
            self.behavioural_flags.get("temperature_control", {}).get(
                "range", [0.2, 0.6]
            ),
        )
        self.response_validator = ResponseValidator(
            self.response_contract.get("output_format", {}).get("required_fields", [])
        )
        logger.info(
            f"BehaviouralContract initialized with version={self.version}, role={self.role}"
        )

    def is_suspicious_behavior(
        self, response: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Detect suspicious behavior by comparing response with context.

        A decision is considered suspicious if:
        1. Both current and previous decisions are high confidence
        2. The decisions are significantly different (not just minor variations)
        3. The change is unexpected given the context
        """
        if not context or "memory" not in context:
            logger.warning(
                "No context or memory provided for suspicious behavior check"
            )
            return False

        # Get the behavior key from the contract's behavior signature
        behavior_key = (
            self.response_contract.get("behaviour_signature", {}).get("key", "decision")
            if self.response_contract.get("behaviour_signature")
            else "decision"
        )

        current_behavior = response.get(behavior_key, "").lower()
        current_confidence = response.get("confidence", "").lower()
        if not current_behavior or current_confidence != "high":
            logger.info(f"No high confidence {behavior_key} in current response")
            return False

        stale_memory = context.get("memory", [])
        if not stale_memory:
            logger.warning("No stale memory found in context")
            return False

        latest_memory = stale_memory[0].get("analysis", {})
        stale_behavior = latest_memory.get(behavior_key, "").lower()
        stale_confidence = latest_memory.get("confidence", "").lower()
        if not stale_behavior or stale_confidence != "high":
            logger.info(f"No high confidence {behavior_key} in stale memory")
            return False

        logger.info(
            f"Comparing {behavior_key}s - Stale: {stale_behavior} ({stale_confidence}), Current: {current_behavior}"
        )

        # Check if the decisions are significantly different
        # For now, we consider them different if they're not the same
        # In the future, we could use more sophisticated similarity metrics
        if stale_behavior != current_behavior:
            # Check if the change is unexpected given the context
            # For example, if the context suggests the same decision should be made
            context_suggestion = context.get("context_suggestion", "").lower()
            if context_suggestion and context_suggestion == stale_behavior:
                logger.warning(
                    f"Suspicious behavior detected: Response {current_behavior} contradicts context suggestion {context_suggestion}"
                )
                return True

            # Check if the change breaks an established pattern
            pattern_history = context.get("pattern_history", [])
            if pattern_history and all(
                p.lower() == stale_behavior for p in pattern_history[-3:]
            ):
                logger.warning(
                    f"Suspicious behavior detected: Response {current_behavior} breaks from established pattern {pattern_history}"
                )
                return True

            # If we get here, the change might be suspicious but not definitively
            # We'll log it but not flag it as suspicious
            logger.info(
                f"Decision changed from {stale_behavior} to {current_behavior}, but not definitively suspicious"
            )

        logger.info("No suspicious behavior detected")
        return False

    def log_contract_event(self, event_type: str, data: Dict[str, Any]) -> None:
        logger.info(
            json.dumps(
                {
                    "timestamp": datetime.now().isoformat(),
                    "event_type": event_type,
                    "contract_version": self.version,
                    "role": self.role,
                    "data": data,
                }
            )
        )

    def handle_escalation(self, reason: str) -> None:
        escalation_action = getattr(self.escalation, f"on_{reason}", "fallback")
        logger.warning(
            f"Handling escalation for reason: {reason}, action: {escalation_action}"
        )
        self.log_contract_event(
            "escalation", {"reason": reason, "action": escalation_action}
        )


def _create_fallback_response(
    contract_spec: Dict[str, Any], reason: str
) -> Dict[str, Any]:
    """Create a fallback response with the given reason."""
    fallback = contract_spec["response_contract"]["output_format"]["on_failure"][
        "fallback"
    ].copy()
    fallback["reasoning"] = reason
    for field in ["flagged_for_review", "strike_reason", "temperature_used"]:
        if field not in fallback:
            fallback[field] = None if field != "flagged_for_review" else False
    return dict(fallback)


def _handle_suspicious_behavior(
    result: Dict[str, Any], kwargs: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle suspicious behavior detection."""
    if is_suspicious_behavior(result, kwargs):
        logger.warning("Suspicious behavior detected")
        result = result.copy()
        result["flagged_for_review"] = True
        result["strike_reason"] = "High confidence decision changed unexpectedly"
    return result


def _validate_response(
    result: Dict[str, Any], contract_spec: Dict[str, Any]
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Validate the response against the contract requirements."""
    try:
        from behavioural_contracts.validator import validate_response

        validate_response(
            result,
            contract_spec["response_contract"]["output_format"],
            contract_spec["policy"],
            contract_spec.get("behavioural_flags", {}),
        )
        logger.info("Response validation passed")
        return True, None
    except BehaviouralContractViolationError as e:
        logger.warning(f"Response validation failed: {e!s}")
        fallback = _create_fallback_response(contract_spec, str(e))
        return False, fallback


def behavioural_contract(
    version: str,
    description: str,
    role: str,
    policy: Dict[str, Any],
    behavioural_flags: Dict[str, Any],
    response_contract: Dict[str, Any],
    health: Optional[Dict[str, Any]] = None,
    escalation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a behavioural contract.

    Args:
        version: Contract version
        description: Contract description
        role: Agent role
        policy: Policy configuration
        behavioural_flags: Behavioural flags configuration
        response_contract: Response contract configuration
        health: Optional health configuration
        escalation: Optional escalation configuration

    Returns:
        The behavioural contract
    """
    contract = {
        "version": version,
        "description": description,
        "role": role,
        "policy": policy,
        "behavioural_flags": behavioural_flags,
        "response_contract": response_contract,
    }

    if health:
        contract["health"] = health
    if escalation:
        contract["escalation"] = escalation

    return contract


def validate_contract(contract: Dict[str, Any]) -> None:
    """Validate a behavioural contract.

    Args:
        contract: The contract to validate

    Raises:
        BehaviouralContractViolationError: If the contract is invalid
    """
    # Validate version
    if not contract.get("version"):
        raise BehaviouralContractViolationError("Contract version is required")

    # Validate description
    if not contract.get("description"):
        raise BehaviouralContractViolationError("Contract description is required")

    # Validate role
    if not contract.get("role"):
        raise BehaviouralContractViolationError("Contract role is required")

    # Validate policy
    if not contract.get("policy", {}).get("compliance_tags"):
        raise BehaviouralContractViolationError(
            "At least one compliance tag is required"
        )
    if not contract.get("policy", {}).get("allowed_tools"):
        raise BehaviouralContractViolationError("At least one allowed tool is required")

    # Validate behavioural flags
    if not contract.get("behavioural_flags", {}).get("conservatism"):
        raise BehaviouralContractViolationError("Conservatism level is required")
    if not contract.get("behavioural_flags", {}).get("verbosity"):
        raise BehaviouralContractViolationError("Verbosity level is required")


def is_suspicious_behavior(
    response: Dict[str, Any], context: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """Check if response indicates suspicious behavior.

    Args:
        response: The response to check
        context: Optional context information

    Returns:
        Tuple of (is_suspicious, reason)
    """
    # Check for high confidence decision changes
    if context and "memory" in context:
        memory = context["memory"]
        if memory:
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
                return True, "high confidence decision changed"

    return False, ""
