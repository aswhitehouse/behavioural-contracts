import json
import functools
import time
import logging
from typing import Dict, Optional, Callable, Any
from datetime import datetime
from functools import wraps

from .health_monitor import HealthMonitor
from .temperature import TemperatureController
from .validator import ResponseValidator, try_parse_json
from .models import BehavioralContractSpec

logger = logging.getLogger(__name__)

class BehavioralContract:
    def __init__(self, contract_spec: Dict):
        # Validate and parse the contract specification
        self.spec = BehavioralContractSpec(**contract_spec)
        
        # Initialize components
        self.health_monitor = HealthMonitor()
        self.temp_controller = TemperatureController(
            self.spec.behavioral_flags.temperature_control.mode,
            self.spec.behavioral_flags.temperature_control.range
        )
        self.response_validator = ResponseValidator(
            self.spec.response_contract.output_format.required_fields
        )
        logger.info(f"BehavioralContract initialized with version={self.spec.version}, role={self.spec.role}")

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
            "contract_version": self.spec.version,
            "role": self.spec.role,
            "data": data
        }))

    def handle_escalation(self, reason: str):
        escalation_action = getattr(self.spec.escalation, f"on_{reason}", "fallback")
        logger.warning(f"Handling escalation for reason: {reason}, action: {escalation_action}")
        self.log_contract_event("escalation", {
            "reason": reason,
            "action": escalation_action
        })

def behavioral_contract(contract_spec: Dict[str, Any]):
    """Decorator to enforce behavioral contracts on functions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Dict[str, Any]:
            try:
                # Parse and validate contract spec
                spec = BehavioralContractSpec(**contract_spec)
                required_fields = spec.response_contract.output_format.required_fields
                validator = ResponseValidator(required_fields=required_fields)
                validator.start_timer()
                response = func(*args, **kwargs)
                is_valid, reason = validator.validate(
                    response,
                    spec.policy,
                    spec.behavioral_flags,
                    spec.response_contract,
                    kwargs
                )
                if not is_valid:
                    logger.warning(f"Response validation failed: {reason}")
                    fallback = validator.get_fallback_response(reason)
                    # If high confidence change, add flag for review
                    if 'high confidence recommendation changed' in reason:
                        fallback['flagged_for_review'] = True
                        fallback['strike_reason'] = 'Suspicious output based on stale context or mismatch'
                    # If temperature_used was in the response, include it in fallback for test compatibility
                    if 'temperature_used' in response:
                        fallback['temperature_used'] = response['temperature_used']
                    return fallback
                if validator.should_resubmit(response, kwargs.get('context')):
                    logger.info("Resubmitting with adjusted parameters")
                    return func(*args, **kwargs)
                return response
            except Exception as e:
                logger.error(f"Contract enforcement error: {str(e)}")
                return {
                    "recommendation": "unknown",
                    "confidence": "low",
                    "summary": "An error occurred during contract enforcement.",
                    "reasoning": str(e)
                }
        return wrapper
    return decorator