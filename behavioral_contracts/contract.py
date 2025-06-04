import json
import functools
import time
import logging
from typing import Dict, Optional, Callable
from datetime import datetime

from .health_monitor import HealthMonitor
from .temperature import TemperatureController
from .validator import ResponseValidator, try_parse_json

logger = logging.getLogger(__name__)

class BehavioralContract:
    def __init__(self, contract_spec: Dict):
        self.version = contract_spec.get("version", "1.0")
        self.description = contract_spec.get("description", "")
        self.role = contract_spec.get("role", "default")
        self.policy = contract_spec.get("policy", {})
        self.behavioral_flags = contract_spec.get("behavioral_flags", {})
        self.response_contract = contract_spec.get("response_contract", {})
        self.health = contract_spec.get("health", {})
        self.escalation = contract_spec.get("escalation", {})

        # Initialize components
        self.health_monitor = HealthMonitor()
        self.temp_controller = TemperatureController(
            self.behavioral_flags.get("temperature_control", {}).get("mode", "fixed"),
            self.behavioral_flags.get("temperature_control", {}).get("range", [0.2, 0.6])
        )
        self.response_validator = ResponseValidator(
            self.response_contract.get("output_format", {}).get("required_fields", [])
        )
        logger.info(f"BehavioralContract initialized with version={self.version}, role={self.role}")

    def is_suspicious_behavior(self, response: dict, context: dict = None) -> bool:
        """Detect suspicious behavior by comparing response with context."""
        if not context or 'memory' not in context:
            logger.warning("No context or memory provided for suspicious behavior check")
            return False

        # Get the current recommendation
        current_rec = response.get('recommendation', '').lower()
        if not current_rec:
            logger.warning("No recommendation in current response")
            return False

        # Get the stale memory recommendation
        stale_memory = context.get('memory', [])
        if not stale_memory:
            logger.warning("No stale memory found in context")
            return False

        # Get the most recent memory
        latest_memory = stale_memory[0].get('analysis', {})
        stale_rec = latest_memory.get('recommendation', '').lower()
        stale_confidence = latest_memory.get('confidence', '').lower()
        if not stale_rec:
            logger.warning("No recommendation in stale memory")
            return False

        logger.info(f"Comparing recommendations - Stale: {stale_rec} ({stale_confidence}), Current: {current_rec}")

        # Check for suspicious behavior:
        # 1. If the model had a high confidence recommendation and is now changing it
        #    This is suspicious because high confidence recommendations should be more stable
        if stale_confidence == 'high' and stale_rec != current_rec:
            logger.warning(f"Suspicious behavior detected: Changing high confidence recommendation from {stale_rec} to {current_rec}")
            return True
        
        # 2. If stale memory is bullish and current indicators are extremely bearish
        #    but the model maintains the bullish recommendation
        indicators = context.get('indicators', {})
        if not indicators:
            logger.warning("No indicators found in context")
            return False

        is_extremely_bearish = (
            indicators.get('rsi', 50) < 30 or  # Oversold
            (indicators.get('ema_50', 0) < indicators.get('ema_200', 0)) or  # Death cross
            indicators.get('trend', '') == 'strong_downtrend'  # Strong downtrend
        )
        
        if stale_rec == 'buy' and is_extremely_bearish and current_rec == 'buy':
            logger.warning("Suspicious behavior detected: Bullish recommendation despite extremely bearish indicators")
            return True

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
        escalation_action = self.escalation.get(f"on_{reason}", "fallback")
        logger.warning(f"Handling escalation for reason: {reason}, action: {escalation_action}")
        self.log_contract_event("escalation", {
            "reason": reason,
            "action": escalation_action
        })

def behavioral_contract(contract_spec: Dict, contract_instance: Optional[BehavioralContract] = None):
    # Use provided contract instance or create a new one
    contract = contract_instance or BehavioralContract(contract_spec)
    logger.info(f"Behavioral contract decorator initialized with {'provided' if contract_instance else 'new'} instance")
    
    def decorator(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            logger.info(f"Behavioral contract wrapper called for function: {fn.__name__}")
            start_time = time.time()
            
            # Check health status
            if contract.health_monitor.status == "unhealthy":
                logger.warning("Agent is unhealthy, using fallback response")
                contract.log_contract_event("health_check", {
                    "status": "unhealthy",
                    "action": "fallback"
                })
                return contract.response_contract["output_format"]["on_failure"]["fallback"]

            # Execute with retries
            max_retries = contract.response_contract["output_format"]["on_failure"].get("max_retries", 1)
            for attempt in range(max_retries + 1):
                logger.info(f"Attempt {attempt + 1} of {max_retries + 1}")
                try:
                    # Get current temperature
                    current_temp = contract.temp_controller.get_temperature()
                    logger.info(f"Executing function with temperature: {current_temp}")
                    
                    # Call the function with temperature in kwargs if it accepts it
                    try:
                        raw_response = fn(*args, temperature=current_temp, **kwargs)
                    except TypeError:
                        raw_response = fn(*args, **kwargs)
                    
                    # If response is a string, try to parse it
                    if isinstance(raw_response, str):
                        parsed_response = try_parse_json(raw_response)
                        if parsed_response is not None:
                            raw_response = parsed_response

                    # Validate response format
                    if contract.response_validator.validate(raw_response):
                        # Check for suspicious behavior
                        context = {
                            'memory': kwargs.get('memory', []),
                            'indicators': kwargs.get('indicators', {})
                        }
                        logger.info(f"Checking for suspicious behavior with context: {context}")
                        
                        if contract.is_suspicious_behavior(raw_response, context):
                            logger.warning("Suspicious behavior detected - logging strike and flagging for review")
                            contract.health_monitor.add_strike("suspicious_behavior")
                            contract.handle_escalation("unexpected_output")
                            
                            # Add flags to response
                            raw_response = dict(raw_response)  # Ensure we can modify the response
                            raw_response["flagged_for_review"] = True
                            raw_response["strike_reason"] = "Suspicious output based on stale context or mismatch"

                        # Response time check
                        response_time = (time.time() - start_time) * 1000
                        if response_time > contract.response_contract.get("max_response_time_ms", 5000):
                            logger.warning(f"Response time {response_time}ms exceeded threshold")
                            contract.log_contract_event("performance_warning", {
                                "response_time_ms": response_time,
                                "threshold_ms": contract.response_contract["max_response_time_ms"]
                            })

                        contract.temp_controller.adjust(True)
                        logger.info("Function execution successful")
                        return raw_response

                    # If we get here, validation failed
                    logger.warning("Response validation failed")
                    contract.temp_controller.adjust(False)
                    contract.health_monitor.add_strike("invalid_response_format")
                    
                    if attempt < max_retries:
                        continue

                except Exception as e:
                    logger.error(f"Function execution failed: {str(e)}")
                    contract.log_contract_event("error", {
                        "error": str(e),
                        "attempt": attempt + 1
                    })
                    contract.temp_controller.adjust(False)
                    contract.health_monitor.add_strike(str(e))

            # If we get here, all retries failed
            logger.warning("All attempts failed, escalating to fallback")
            contract.handle_escalation("unexpected_output")
            return contract.response_contract["output_format"]["on_failure"]["fallback"]

        return wrapper
    return decorator