import json
import logging
from typing import Dict, Callable, Any
from datetime import datetime
from functools import wraps

from .health_monitor import HealthMonitor
from .temperature import TemperatureController
from .validator import ResponseValidator
from .models import BehavioralContractSpec

logger = logging.getLogger(__name__)

class BehavioralContract:
    def __init__(self, contract_spec: Dict):
        self.spec = BehavioralContractSpec(**contract_spec)
        
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
        """Detect suspicious behavior by comparing response with context.
        
        The behavior signature allows tracking any field as the behavior anchor.
        For example, if behavior_signature = {"key": "goal"}, then changes in the
        "goal" field will be tracked instead of "decision".
        
        General patterns that might indicate suspicious behavior:
        1. High confidence changes - if a system was very confident about a behavior
           and suddenly changes it, this might be suspicious
        2. Context mismatch - if the current context suggests one thing but the
           response suggests another, this might be suspicious
        3. Pattern breaks - if the system suddenly breaks from established patterns
           without clear reason
        """
        if not context or 'memory' not in context:
            logger.warning("No context or memory provided for suspicious behavior check")
            return False

        behavior_key = (
            self.spec.response_contract.behavior_signature.get("key", "decision")
            if self.spec.response_contract.behavior_signature
            else "decision"
        )

        if not self.spec.response_contract.behavior_signature:
            logger.warning("No behavior signature defined - skipping behavior tracking")
            return False

        current_behavior = response.get(behavior_key, '').lower()
        if not current_behavior:
            logger.warning(f"No {behavior_key} in current response")
            return False

        stale_memory = context.get('memory', [])
        if not stale_memory:
            logger.warning("No stale memory found in context")
            return False

        latest_memory = stale_memory[0].get('analysis', {})
        stale_behavior = latest_memory.get(behavior_key, '').lower()
        stale_confidence = latest_memory.get('confidence', '').lower()
        if not stale_behavior:
            logger.warning(f"No {behavior_key} in stale memory")
            return False

        logger.info(f"Comparing {behavior_key}s - Stale: {stale_behavior} ({stale_confidence}), Current: {current_behavior}")

        if stale_confidence == 'high' and stale_behavior != current_behavior:
            logger.warning(f"Suspicious behavior detected: Changing high confidence {behavior_key} from {stale_behavior} to {current_behavior}")
            return True

        context_suggestion = context.get('context_suggestion', '')
        if context_suggestion and context_suggestion.lower() != current_behavior:
            logger.warning(f"Suspicious behavior detected: Response {current_behavior} contradicts context suggestion {context_suggestion}")
            return True

        pattern_history = context.get('pattern_history', [])
        if pattern_history and current_behavior not in pattern_history:
            logger.warning(f"Suspicious behavior detected: Response {current_behavior} breaks from established pattern {pattern_history}")
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
                spec = BehavioralContractSpec(**contract_spec)
                required_fields = spec.response_contract.output_format.required_fields
                validator = ResponseValidator(required_fields=required_fields)
                validator.start_timer()
                response = func(*args, **kwargs)
                
                policy = spec.policy.model_dump() if hasattr(spec.policy, 'model_dump') else (spec.policy.dict() if hasattr(spec.policy, 'dict') else dict(spec.policy))
                behavioral_flags = spec.behavioral_flags.model_dump() if hasattr(spec.behavioral_flags, 'model_dump') else (spec.behavioral_flags.dict() if hasattr(spec.behavioral_flags, 'dict') else dict(spec.behavioral_flags))
                response_contract = spec.response_contract.model_dump() if hasattr(spec.response_contract, 'model_dump') else (spec.response_contract.dict() if hasattr(spec.response_contract, 'dict') else dict(spec.response_contract))
                is_valid, reason = validator.validate(
                    response,
                    policy,
                    behavioral_flags,
                    response_contract,
                    kwargs
                )
                if not is_valid:
                    logger.warning(f"Response validation failed: {reason}")
                    fallback = validator.get_fallback_response(reason)
                
                    if 'high confidence decision changed' in reason:
                        fallback['flagged_for_review'] = True
                        fallback['strike_reason'] = 'Suspicious output based on stale context or mismatch'
                
                    if 'temperature_used' in response:
                        fallback['temperature_used'] = response['temperature_used']
                    return fallback
                
                contract = BehavioralContract(contract_spec)
                
                context = kwargs.get('context')
                if context is None:
                
                    context = {
                        'memory': kwargs.get('memory', []),
                        'indicators': kwargs.get('indicators', {})
                    }
                if contract.is_suspicious_behavior(response, context):
                    response['flagged_for_review'] = True
                    response['strike_reason'] = 'Suspicious output based on stale context or mismatch'
                if validator.should_resubmit(response, kwargs.get('context')):
                    logger.info("Resubmitting with adjusted parameters")
                    return func(*args, **kwargs)
                return response
            except Exception as e:
                logger.error(f"Contract enforcement error: {str(e)}")
                fallback = {
                    "decision": "unknown",
                    "confidence": "low",
                    "summary": "An error occurred during contract enforcement.",
                    "reasoning": str(e)
                }
                
                if 'response' in locals() and isinstance(response, dict) and 'temperature_used' in response:
                    fallback['temperature_used'] = response['temperature_used']
                return fallback
        return wrapper
    return decorator