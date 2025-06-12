import json
import logging
from typing import Dict
from datetime import datetime
from functools import wraps
import time

from .health_monitor import HealthMonitor
from .temperature import TemperatureController
from .validator import ResponseValidator
from .exceptions import BehaviouralContractViolation

logger = logging.getLogger(__name__)

class BehaviouralContract:
    def __init__(self, contract_spec: Dict):
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
            self.behavioural_flags.get("temperature_control", {}).get("range", [0.2, 0.6])
        )
        self.response_validator = ResponseValidator(
            self.response_contract.get("output_format", {}).get("required_fields", [])
        )
        logger.info(f"BehaviouralContract initialized with version={self.version}, role={self.role}")

    def is_suspicious_behavior(self, response: dict, context: dict = None) -> bool:
        """Detect suspicious behavior by comparing response with context.
        
        A decision is considered suspicious if:
        1. Both current and previous decisions are high confidence
        2. The decisions are significantly different (not just minor variations)
        3. The change is unexpected given the context
        """
        if not context or 'memory' not in context:
            logger.warning("No context or memory provided for suspicious behavior check")
            return False

        # Get the behavior key from the contract's behavior signature
        behavior_key = (
            self.response_contract.get("behaviour_signature", {}).get("key", "decision")
            if self.response_contract.get("behaviour_signature")
            else "decision"
        )

        current_behavior = response.get(behavior_key, '').lower()
        current_confidence = response.get('confidence', '').lower()
        if not current_behavior or current_confidence != 'high':
            logger.info(f"No high confidence {behavior_key} in current response")
            return False

        stale_memory = context.get('memory', [])
        if not stale_memory:
            logger.warning("No stale memory found in context")
            return False

        latest_memory = stale_memory[0].get('analysis', {})
        stale_behavior = latest_memory.get(behavior_key, '').lower()
        stale_confidence = latest_memory.get('confidence', '').lower()
        if not stale_behavior or stale_confidence != 'high':
            logger.info(f"No high confidence {behavior_key} in stale memory")
            return False

        logger.info(f"Comparing {behavior_key}s - Stale: {stale_behavior} ({stale_confidence}), Current: {current_behavior}")

        # Check if the decisions are significantly different
        # For now, we consider them different if they're not the same
        # In the future, we could use more sophisticated similarity metrics
        if stale_behavior != current_behavior:
            # Check if the change is unexpected given the context
            # For example, if the context suggests the same decision should be made
            context_suggestion = context.get('context_suggestion', '').lower()
            if context_suggestion and context_suggestion == stale_behavior:
                logger.warning(f"Suspicious behavior detected: Response {current_behavior} contradicts context suggestion {context_suggestion}")
                return True

            # Check if the change breaks an established pattern
            pattern_history = context.get('pattern_history', [])
            if pattern_history and all(p.lower() == stale_behavior for p in pattern_history[-3:]):
                logger.warning(f"Suspicious behavior detected: Response {current_behavior} breaks from established pattern {pattern_history}")
                return True

            # If we get here, the change might be suspicious but not definitively
            # We'll log it but not flag it as suspicious
            logger.info(f"Decision changed from {stale_behavior} to {current_behavior}, but not definitively suspicious")

        logger.info("No suspicious behavior detected")
        return False

    def log_contract_event(self, event_type: str, data: Dict):
        logger.info(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "contract_version": self.version,
            "role": self.role,
            "data": data
        }))

    def handle_escalation(self, reason: str):
        escalation_action = getattr(self.escalation, f"on_{reason}", "fallback")
        logger.warning(f"Handling escalation for reason: {reason}, action: {escalation_action}")
        self.log_contract_event("escalation", {
            "reason": reason,
            "action": escalation_action
        })

def behavioural_contract(contract_spec: dict):
    """Decorator that enforces a behavioural contract on a function."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                response_time = time.time() - start_time

                logger.info(f"Function returned result: {result}")

                # Response time check (fix: look in response_contract, not output_format)
                max_time = contract_spec["response_contract"].get("max_response_time_ms")
                if max_time is not None and response_time * 1000 > max_time:
                    logger.warning(f"Response time {response_time*1000:.2f}ms exceeded max {max_time}ms")
                    fallback = contract_spec["response_contract"]["output_format"]["on_failure"]["fallback"].copy()
                    fallback["reasoning"] = f"Response timeout: {response_time*1000:.2f}ms exceeds maximum allowed time ({max_time}ms)"
                    for field in ["flagged_for_review", "strike_reason", "temperature_used"]:
                        if field not in fallback:
                            fallback[field] = None if field != "flagged_for_review" else False
                    logger.info(f"Returning fallback due to response time: {fallback}")
                    return fallback

                # Check for suspicious behavior
                if is_suspicious_behavior(result, kwargs.get('memory', []), contract_spec["response_contract"]):
                    logger.warning("Suspicious behavior detected")
                    result = result.copy()  # Create a copy to avoid modifying the original
                    result["flagged_for_review"] = True
                    result["strike_reason"] = "High confidence decision changed unexpectedly"

                # Validate response using the correct contract section
                logger.info("Calling validate_response...")
                try:
                    # Pass behavioural_flags as well for temperature validation
                    from behavioural_contracts.validator import validate_response
                    validate_response(
                        result,
                        contract_spec["response_contract"]["output_format"],
                        contract_spec["policy"],
                        contract_spec.get("behavioural_flags", {})
                    )
                    logger.info("Response validation passed")
                except BehaviouralContractViolation as e:
                    logger.warning(f"Response validation failed: {str(e)}")
                    fallback = contract_spec["response_contract"]["output_format"]["on_failure"]["fallback"].copy()
                    fallback["reasoning"] = str(e)
                    # Add any other fields expected by tests if missing
                    for field in ["flagged_for_review", "strike_reason", "temperature_used"]:
                        if field not in fallback:
                            fallback[field] = None if field != "flagged_for_review" else False
                    logger.info(f"Returning fallback due to validation failure: {fallback}")
                    return fallback

                # If we get here, the response is valid
                logger.info("Returning valid response")
                return result

            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                fallback = contract_spec["response_contract"]["output_format"]["on_failure"]["fallback"].copy()
                fallback["reasoning"] = f"Error: {str(e)}"
                for field in ["flagged_for_review", "strike_reason", "temperature_used"]:
                    if field not in fallback:
                        fallback[field] = None if field != "flagged_for_review" else False
                return fallback

        return wrapper
    return decorator

def is_suspicious_behavior(result: dict, memory: list, contract: dict) -> bool:
    """Check if the current behavior is suspicious compared to memory."""
    if not memory:
        return False

    # Get the key to track from the contract
    key = contract.get("behaviour_signature", {}).get("key", "decision")
    
    # Get current and previous decisions
    current_decision = result.get(key)
    current_confidence = result.get("confidence", "low")
    
    # Get the last high confidence decision from memory
    last_high_conf = None
    for entry in reversed(memory):
        if isinstance(entry, dict) and "analysis" in entry:
            if entry["analysis"].get("confidence") == "high":
                last_high_conf = entry["analysis"].get(key)
                break

    if not last_high_conf or current_confidence != "high":
        return False

    # Check if the change is suspicious
    if current_decision != last_high_conf:
        # For now, we consider any high confidence change to be suspicious
        # In the future, we could add more sophisticated checks
        return True

    return False