import functools
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Tuple, Union

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

        # If both are high confidence and different, it's suspicious
        if current_behavior != stale_behavior:
            logger.warning(
                f"Suspicious behavior detected: {stale_behavior} -> {current_behavior}"
            )
            return True

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
    # Create a simple fallback response
    fallback = {
        "response": "",
        "reasoning": reason,
        "error": "Response validation failed",
    }

    # Add any required fields from the contract
    response_contract = contract_spec.get("response_contract", {})
    if response_contract:
        output_format = response_contract.get("output_format", {})
        required_fields = output_format.get("required_fields", [])
        for field in required_fields:
            if field not in fallback:
                if field == "response":
                    fallback[field] = ""
                elif field == "confidence":
                    fallback[field] = "low"
                elif field == "decision":
                    fallback[field] = "unknown"
                else:
                    fallback[field] = ""

    return fallback


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
        # Simple validation: just check if the response is not empty
        if not result:
            logger.warning("Response is empty")
            raise BehaviouralContractViolationError("Response is empty")

        # If response_contract specifies required fields, validate them
        response_contract = contract_spec.get("response_contract", {})
        if response_contract:
            output_format = response_contract.get("output_format", {})
            required_fields = output_format.get("required_fields", [])

            if required_fields:
                for field in required_fields:
                    if field not in result:
                        logger.warning(f"Missing required field: {field}")
                        raise BehaviouralContractViolationError(
                            f"Missing required field: {field}"
                        )

        logger.info("Response validation passed")
        return True, None
    except BehaviouralContractViolationError as e:
        logger.warning(f"Response validation failed: {e!s}")
        fallback = _create_fallback_response(contract_spec, str(e))
        return False, fallback


def _parse_contract_string(contract_str: str) -> Dict[str, Any]:
    """Parse a contract specification string into a dictionary.

    Args:
        contract_str: String containing the contract specification

    Returns:
        Dictionary containing the parsed contract specification

    Raises:
        BehaviouralContractViolationError: If parsing fails
    """
    try:
        # Remove any whitespace and newlines
        contract_str = contract_str.strip()
        # Create a dictionary from the key-value pairs
        contract_dict: Dict[str, Any] = {}
        for line in contract_str.split(","):
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # Convert string values to Python objects
                if value.startswith("{") and value.endswith("}"):
                    parsed_value = json.loads(value)
                elif value.startswith("[") and value.endswith("]"):
                    parsed_value = json.loads(value)
                elif value.lower() in ("true", "false"):
                    parsed_value = value.lower() == "true"
                elif value.isdigit():
                    parsed_value = int(value)
                elif value.replace(".", "").isdigit():
                    parsed_value = float(value)
                else:
                    # Remove quotes from string values
                    parsed_value = value.strip("\"'")
                contract_dict[key] = parsed_value
        return contract_dict
    except Exception as e:
        raise BehaviouralContractViolationError(
            f"Failed to parse contract specification: {e!s}"
        ) from e


def _normalize_result(result: Any) -> Dict[str, Any]:
    """Normalize the result to ensure it's a dictionary.

    Args:
        result: The result from the decorated function

    Returns:
        Normalized dictionary result
    """
    if not isinstance(result, dict):
        logger.warning(f"Result is not a dictionary: {type(result)}")
        # Try to convert to dictionary if it's a Pydantic model
        if hasattr(result, "model_dump"):
            result_dict = result.model_dump()
        elif hasattr(result, "dict"):
            result_dict = result.dict()
        else:
            # Create a simple dictionary with the result
            result_dict = {"response": str(result)}
        return result_dict  # type: ignore
    return result


def _create_wrapper(
    func: Callable[..., Any],
    contract_spec: Dict[str, Any],
    contract: BehaviouralContract,
) -> Callable[..., Any]:
    """Create the wrapper function for the decorator.

    Args:
        func: The function to wrap
        contract_spec: The contract specification
        contract: The behavioural contract instance

    Returns:
        Wrapped function
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            # Execute the function
            result = func(*args, **kwargs)

            # Normalize the result
            result = _normalize_result(result)

            # Debug: log what we're about to validate
            logger.info(f"About to validate result: {result}")
            logger.info(
                f"Required fields: {contract_spec.get('response_contract', {}).get('output_format', {}).get('required_fields', [])}"
            )

            # Validate the response
            is_valid, fallback = _validate_response(result, contract_spec)
            if not is_valid:
                logger.warning("Response validation failed, using fallback")
                return fallback

            # Check for suspicious behavior
            if contract.is_suspicious_behavior(result, kwargs.get("context")):
                logger.warning("Suspicious behavior detected")
                contract.handle_escalation("suspicious_behavior")

            # Log the contract event
            contract.log_contract_event(
                "function_call",
                {
                    "function": func.__name__,
                    "args": args,
                    "kwargs": kwargs,
                    "result": result,
                },
            )

            return result
        except Exception as e:
            logger.error(f"Error in wrapped function: {e!s}")
            contract.handle_escalation("error")
            raise

    return wrapper


def behavioural_contract(
    contract_spec: Optional[Union[Dict[str, Any], str]] = None, **kwargs: Any
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Create a behavioural contract decorator.

    Args:
        contract_spec: Either a dictionary containing the contract specification,
                      or a string containing the contract specification in decorator format.
        **kwargs: Keyword arguments for the contract specification.

    Returns:
        A decorator function that wraps the decorated function with the behavioural contract.

    Example:
        # Using a dictionary
        @behavioural_contract({
            "version": "1.1",
            "description": "Test agent",
            "role": "test",
            "policy": {
                "pii": False,
                "compliance_tags": ["TEST-TAG"],
                "allowed_tools": ["test_tool"]
            }
        })
        def my_agent():
            pass

        # Using keyword arguments
        @behavioural_contract(
            version="1.1",
            description="Test agent",
            role="test",
            policy={
                "pii": False,
                "compliance_tags": ["TEST-TAG"],
                "allowed_tools": ["test_tool"]
            }
        )
        def my_agent():
            pass

        # Using a string
        @behavioural_contract('''
            version="1.1",
            description="Test agent",
            role="test",
            policy={
                "pii": False,
                "compliance_tags": ["TEST-TAG"],
                "allowed_tools": ["test_tool"]
            }
        ''')
        def my_agent():
            pass
    """
    # If kwargs are provided, use them as the contract specification
    if kwargs:
        contract_spec = kwargs

    # Parse string contract if provided
    if isinstance(contract_spec, str):
        contract_spec = _parse_contract_string(contract_spec)

    # Ensure contract_spec is not None at this point
    if contract_spec is None:
        raise BehaviouralContractViolationError("Contract specification is required")

    # Validate the contract
    validate_contract(contract_spec)

    # Create the contract instance
    contract = BehaviouralContract(contract_spec)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return _create_wrapper(func, contract_spec, contract)

    return decorator


def _validate_required_fields(contract: Dict[str, Any]) -> None:
    """Validate the required fields in a contract.

    Args:
        contract: The contract to validate

    Raises:
        BehaviouralContractViolationError: If any required field is missing
    """
    if not contract.get("version"):
        raise BehaviouralContractViolationError("Contract version is required")

    if not contract.get("description"):
        raise BehaviouralContractViolationError("Contract description is required")

    if not contract.get("role"):
        raise BehaviouralContractViolationError("Contract role is required")


def _validate_optional_fields(contract: Dict[str, Any]) -> None:
    """Validate the optional fields in a contract.

    Args:
        contract: The contract to validate

    Raises:
        BehaviouralContractViolationError: If any optional field has invalid type
    """
    optional_fields = [
        "behavioural_flags",
        "response_contract",
        "policy",
        "memory_config",
        "teardown_policy",
    ]

    for field in optional_fields:
        if field in contract:
            field_value = contract[field]
            if not isinstance(field_value, dict):
                raise BehaviouralContractViolationError(f"{field} must be a dictionary")


def validate_contract(contract: Dict[str, Any]) -> None:
    """Validate a behavioural contract.

    Args:
        contract: The contract to validate

    Raises:
        BehaviouralContractViolationError: If the contract is invalid
    """
    _validate_required_fields(contract)
    _validate_optional_fields(contract)


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
