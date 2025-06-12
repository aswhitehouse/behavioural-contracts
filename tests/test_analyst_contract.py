from typing import Any, Dict, cast

from behavioural_contracts.contract import (
    BehaviouralContract,
    _validate_response,
    behavioural_contract,
)

# Test contract specification
ANALYST_CONTRACT = {
    "version": "1.1",
    "description": "Base behavioural contract for the Analyst Agent.",
    "role": "analyst",
    "policy": {
        "pii": False,
        "compliance_tags": ["EU-AI-ACT"],
        "allowed_tools": ["search", "summary", "confidence_estimator"],
    },
    "behavioural_flags": {
        "conservatism": "moderate",
        "verbosity": "compact",
        "temperature_control": {"mode": "adaptive", "range": [0.2, 0.6]},
    },
    "response_contract": {
        "output_format": {
            "type": "object",
            "required_fields": [
                "decision",
                "confidence",
                "summary",
                "reasoning",
                "compliance_tags",
                "temperature_used",
            ],
            "on_failure": {
                "action": "fallback",
                "max_retries": 1,
                "fallback": {
                    "decision": "unknown",
                    "confidence": "low",
                    "summary": "Recommendation rejected due to suspicious behaviour.",
                    "reasoning": "The model's decision was rejected because it changed a high confidence decision too quickly. This requires additional validation.",
                },
            },
        },
        "max_response_time_ms": 1,
        "behaviour_signature": {"key": "decision", "expected_type": "string"},
    },
    "health": {"strikes": 0, "status": "healthy"},
    "escalation": {
        "on_unexpected_output": "flag_for_review",
        "on_context_mismatch": "flag_for_review",
        "fallback_role": "SafeAnalyst",
    },
}


def test_valid_response():
    contract = behavioural_contract(
        version="1.1",
        description="Base behavioural contract for the Analyst Agent.",
        role="analyst",
        policy={
            "pii": False,
            "compliance_tags": ["EU-AI-ACT"],
            "allowed_tools": ["search", "summary", "confidence_estimator"],
        },
        behavioural_flags={
            "conservatism": "moderate",
            "verbosity": "compact",
            "temperature_control": {"mode": "adaptive", "range": [0.2, 0.6]},
        },
        response_contract={
            "output_format": {
                "type": "object",
                "required_fields": [
                    "decision",
                    "confidence",
                    "summary",
                    "reasoning",
                    "compliance_tags",
                    "temperature_used",
                ],
                "on_failure": {
                    "action": "fallback",
                    "max_retries": 1,
                    "fallback": {
                        "decision": "unknown",
                        "confidence": "low",
                        "summary": "Recommendation rejected due to suspicious behaviour.",
                        "reasoning": "The model's decision was rejected because it changed a high confidence decision too quickly. This requires additional validation.",
                    },
                },
            },
            "max_response_time_ms": 1,
            "behaviour_signature": {"key": "decision", "expected_type": "string"},
        },
        health={"strikes": 0, "status": "healthy"},
        escalation={
            "on_unexpected_output": "flag_for_review",
            "on_context_mismatch": "flag_for_review",
            "fallback_role": "SafeAnalyst",
        },
    )

    behavioural_contract_obj = BehaviouralContract(contract)

    def analyst_agent(signal: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        return {
            "decision": "BUY",
            "confidence": "high",
            "summary": "Strong buy signal based on technical indicators",
            "reasoning": "Multiple indicators show bullish momentum",
            "compliance_tags": ["EU-AI-ACT"],
            "tools": ["search", "confidence_estimator"],
            "temperature_used": 0.3,
        }

    result = analyst_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "BUY"
    assert result["confidence"] == "high"
    assert "summary" in result
    assert "reasoning" in result
    assert "EU-AI-ACT" in result["compliance_tags"]
    assert not behavioural_contract_obj.is_suspicious_behavior(result)


def test_pii_detection():
    contract = behavioural_contract(
        version="1.1",
        description="Base behavioural contract for the Analyst Agent.",
        role="analyst",
        policy={
            "pii": False,
            "compliance_tags": ["EU-AI-ACT"],
            "allowed_tools": ["search", "summary", "confidence_estimator"],
        },
        behavioural_flags={
            "conservatism": "moderate",
            "verbosity": "compact",
            "temperature_control": {"mode": "adaptive", "range": [0.2, 0.6]},
        },
        response_contract={
            "output_format": {
                "type": "object",
                "required_fields": [
                    "decision",
                    "confidence",
                    "summary",
                    "reasoning",
                    "compliance_tags",
                    "temperature_used",
                ],
                "on_failure": {
                    "action": "fallback",
                    "max_retries": 1,
                    "fallback": {
                        "decision": "unknown",
                        "confidence": "low",
                        "summary": "Recommendation rejected due to suspicious behaviour.",
                        "reasoning": "The model's decision was rejected because it changed a high confidence decision too quickly. This requires additional validation.",
                    },
                },
            },
            "max_response_time_ms": 1,
            "behaviour_signature": {"key": "decision", "expected_type": "string"},
        },
    )

    behavioural_contract_obj = BehaviouralContract(contract)

    def analyst_agent(signal: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        response = {
            "decision": "BUY",
            "confidence": "high",
            "summary": "Contact us at test@example.com for more details",
            "reasoning": "Multiple indicators show bullish momentum",
            "compliance_tags": ["EU-AI-ACT"],
            "temperature_used": 0.3,
        }
        is_valid, fallback = _validate_response(response, contract)
        if not is_valid and fallback is not None:
            return fallback
        return response

    result = analyst_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert result["confidence"] == "low"
    assert "pii" in result["reasoning"].lower()
    assert not behavioural_contract_obj.is_suspicious_behavior(result)


def test_compliance_tags():
    contract = behavioural_contract(
        version="1.1",
        description="Base behavioural contract for the Analyst Agent.",
        role="analyst",
        policy={
            "pii": False,
            "compliance_tags": ["EU-AI-ACT"],
            "allowed_tools": ["search", "summary", "confidence_estimator"],
        },
        behavioural_flags={
            "conservatism": "moderate",
            "verbosity": "compact",
            "temperature_control": {"mode": "adaptive", "range": [0.2, 0.6]},
        },
        response_contract={
            "output_format": {
                "type": "object",
                "required_fields": [
                    "decision",
                    "confidence",
                    "summary",
                    "reasoning",
                    "compliance_tags",
                    "temperature_used",
                ],
                "on_failure": {
                    "action": "fallback",
                    "max_retries": 1,
                    "fallback": {
                        "decision": "unknown",
                        "confidence": "low",
                        "summary": "Recommendation rejected due to suspicious behaviour.",
                        "reasoning": "The model's decision was rejected because it changed a high confidence decision too quickly. This requires additional validation.",
                    },
                },
            },
            "max_response_time_ms": 1,
            "behaviour_signature": {"key": "decision", "expected_type": "string"},
        },
    )

    behavioural_contract_obj = BehaviouralContract(contract)

    def analyst_agent(signal: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        response = {
            "decision": "BUY",
            "confidence": "high",
            "summary": "Strong buy signal",
            "reasoning": "Multiple indicators show bullish momentum",
            # Missing compliance_tags
        }
        is_valid, fallback = _validate_response(response, contract)
        if not is_valid and fallback is not None:
            return fallback
        return response

    result = analyst_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert result["confidence"] == "low"
    assert "compliance" in result["reasoning"].lower()
    assert not behavioural_contract_obj.is_suspicious_behavior(result)


def test_allowed_tools():
    contract = behavioural_contract(
        version="1.1",
        description="Base behavioural contract for the Analyst Agent.",
        role="analyst",
        policy={
            "pii": False,
            "compliance_tags": ["EU-AI-ACT"],
            "allowed_tools": ["search", "summary", "confidence_estimator"],
        },
        behavioural_flags={
            "conservatism": "moderate",
            "verbosity": "compact",
            "temperature_control": {"mode": "adaptive", "range": [0.2, 0.6]},
        },
        response_contract={
            "output_format": {
                "type": "object",
                "required_fields": [
                    "decision",
                    "confidence",
                    "summary",
                    "reasoning",
                    "compliance_tags",
                    "temperature_used",
                ],
                "on_failure": {
                    "action": "fallback",
                    "max_retries": 1,
                    "fallback": {
                        "decision": "unknown",
                        "confidence": "low",
                        "summary": "Recommendation rejected due to suspicious behaviour.",
                        "reasoning": "The model's decision was rejected because it changed a high confidence decision too quickly. This requires additional validation.",
                    },
                },
            },
            "max_response_time_ms": 1,
            "behaviour_signature": {"key": "decision", "expected_type": "string"},
        },
    )

    behavioural_contract_obj = BehaviouralContract(contract)

    def analyst_agent(signal: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        response = {
            "decision": "BUY",
            "confidence": "high",
            "summary": "Strong buy signal",
            "reasoning": "Multiple indicators show bullish momentum",
            "compliance_tags": ["EU-AI-ACT"],
            "tools": ["unauthorized_tool"],  # Not in allowed_tools
            "temperature_used": 0.3,
        }
        is_valid, fallback = _validate_response(response, contract)
        if not is_valid and fallback is not None:
            return fallback
        return response

    result = analyst_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert result["confidence"] == "low"
    assert "unauthorized" in result["reasoning"].lower()
    assert not behavioural_contract_obj.is_suspicious_behavior(result)


def test_high_confidence_change():
    contract = behavioural_contract(
        version="1.1",
        description="Base behavioural contract for the Analyst Agent.",
        role="analyst",
        policy={
            "pii": False,
            "compliance_tags": ["EU-AI-ACT"],
            "allowed_tools": ["search", "summary", "confidence_estimator"],
        },
        behavioural_flags={
            "conservatism": "moderate",
            "verbosity": "compact",
            "temperature_control": {"mode": "adaptive", "range": [0.2, 0.6]},
        },
        response_contract={
            "output_format": {
                "type": "object",
                "required_fields": [
                    "decision",
                    "confidence",
                    "summary",
                    "reasoning",
                    "compliance_tags",
                    "temperature_used",
                ],
                "on_failure": {
                    "action": "fallback",
                    "max_retries": 1,
                    "fallback": {
                        "decision": "unknown",
                        "confidence": "low",
                        "summary": "Recommendation rejected due to suspicious behaviour.",
                        "reasoning": "The model's decision was rejected because it changed a high confidence decision too quickly. This requires additional validation.",
                    },
                },
            },
            "max_response_time_ms": 1,
            "behaviour_signature": {"key": "decision", "expected_type": "string"},
        },
    )

    behavioural_contract_obj = BehaviouralContract(contract)

    def analyst_agent(signal: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        response = {
            "decision": "SELL",  # Changed from previous BUY
            "confidence": "high",
            "summary": "Strong sell signal",
            "reasoning": "Multiple indicators show bearish momentum",
            "compliance_tags": ["EU-AI-ACT"],
            "temperature_used": 0.3,
        }
        is_valid, fallback = _validate_response(response, contract)
        if not is_valid and fallback is not None:
            return fallback
        context = kwargs if kwargs else None
        print("DEBUG context:", context)
        print("DEBUG response:", response)
        suspicious = behavioural_contract_obj.is_suspicious_behavior(response, context)
        print("DEBUG suspicious:", suspicious)
        if suspicious:
            response["flagged_for_review"] = True
            response["strike_reason"] = "High confidence decision changed unexpectedly"
        return response

    # Test with memory containing previous high confidence decision and pattern history
    memory = [{"analysis": {"decision": "BUY", "confidence": "high"}}]
    pattern_history = ["BUY", "BUY", "BUY"]  # Established pattern
    context = {
        "memory": memory,
        "pattern_history": pattern_history,
        "context_suggestion": "BUY",  # Context suggests BUY
    }
    print("DEBUG memory:", memory)
    print("DEBUG pattern_history:", pattern_history)
    result = analyst_agent({"indicators": {"rsi": 50}}, **context)
    print("DEBUG result:", result)
    assert "flagged_for_review" in result, "flagged_for_review not set in result"
    assert result["flagged_for_review"] is True
    assert "high confidence" in result["strike_reason"].lower()


def test_temperature_control():
    contract = behavioural_contract(
        version="1.1",
        description="Base behavioural contract for the Analyst Agent.",
        role="analyst",
        policy={
            "pii": False,
            "compliance_tags": ["EU-AI-ACT"],
            "allowed_tools": ["search", "summary", "confidence_estimator"],
        },
        behavioural_flags={
            "conservatism": "moderate",
            "verbosity": "compact",
            "temperature_control": {"mode": "adaptive", "range": [0.2, 0.6]},
        },
        response_contract={
            "output_format": {
                "type": "object",
                "required_fields": [
                    "decision",
                    "confidence",
                    "summary",
                    "reasoning",
                    "compliance_tags",
                    "temperature_used",
                ],
                "on_failure": {
                    "action": "fallback",
                    "max_retries": 1,
                    "fallback": {
                        "decision": "unknown",
                        "confidence": "low",
                        "summary": "Recommendation rejected due to suspicious behaviour.",
                        "reasoning": "The model's decision was rejected because it changed a high confidence decision too quickly. This requires additional validation.",
                    },
                },
            },
            "max_response_time_ms": 1,
            "behaviour_signature": {"key": "decision", "expected_type": "string"},
        },
    )

    behavioural_contract_obj = BehaviouralContract(contract)

    def analyst_agent(
        signal: Dict[str, Any], temperature: float = 0.7, **kwargs: Any
    ) -> Dict[str, Any]:
        response = {
            "decision": "BUY",
            "confidence": "high",
            "summary": "Strong buy signal",
            "reasoning": "Multiple indicators show bullish momentum",
            "compliance_tags": ["EU-AI-ACT"],
            "temperature_used": temperature,
        }
        is_valid, fallback = _validate_response(response, contract)
        if not is_valid and fallback is not None:
            return fallback
        return response

    result = analyst_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert result["confidence"] == "low"
    assert "temperature" in result["reasoning"].lower()
    assert not behavioural_contract_obj.is_suspicious_behavior(result)


def test_response_time():
    import time

    from behavioural_contracts.validator import ResponseValidator

    contract = behavioural_contract(
        version="1.1",
        description="Base behavioural contract for the Analyst Agent.",
        role="analyst",
        policy={
            "pii": False,
            "compliance_tags": ["EU-AI-ACT"],
            "allowed_tools": ["search", "summary", "confidence_estimator"],
        },
        behavioural_flags={
            "conservatism": "moderate",
            "verbosity": "compact",
            "temperature_control": {"mode": "adaptive", "range": [0.2, 0.6]},
        },
        response_contract={
            "output_format": {
                "type": "object",
                "required_fields": [
                    "decision",
                    "confidence",
                    "summary",
                    "reasoning",
                    "compliance_tags",
                    "temperature_used",
                ],
                "on_failure": {
                    "action": "fallback",
                    "max_retries": 1,
                    "fallback": {
                        "decision": "unknown",
                        "confidence": "low",
                        "summary": "Recommendation rejected due to suspicious behaviour.",
                        "reasoning": "The model's decision was rejected because it changed a high confidence decision too quickly. This requires additional validation.",
                    },
                },
            },
            "max_response_time_ms": 1,
            "behaviour_signature": {"key": "decision", "expected_type": "string"},
        },
    )
    behavioural_contract_obj = BehaviouralContract(contract)

    def analyst_agent(signal: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        validator = ResponseValidator(
            [
                "decision",
                "confidence",
                "summary",
                "reasoning",
                "compliance_tags",
                "temperature_used",
            ]
        )
        validator.start_timer()
        time.sleep(0.005)  # Simulate slow response
        response = {
            "decision": "BUY",
            "confidence": "high",
            "summary": "Strong buy signal",
            "reasoning": "Multiple indicators show bullish momentum",
            "compliance_tags": ["EU-AI-ACT"],
            "temperature_used": 0.3,
        }
        # Simulate timeout fallback
        is_valid = validator.validate(
            response,
            contract["policy"],
            contract["behavioural_flags"],
            contract["response_contract"],
        )
        if not is_valid[0]:
            return cast(
                Dict[str, Any],
                contract["response_contract"]["output_format"]["on_failure"][
                    "fallback"
                ],
            )
        return response

    result = analyst_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert result["confidence"] == "low"
    assert not behavioural_contract_obj.is_suspicious_behavior(result)


def test_health_monitoring():
    contract = behavioural_contract(
        version="1.1",
        description="Base behavioural contract for the Analyst Agent.",
        role="analyst",
        policy={
            "pii": False,
            "compliance_tags": ["EU-AI-ACT"],
            "allowed_tools": ["search", "summary", "confidence_estimator"],
        },
        behavioural_flags={
            "conservatism": "moderate",
            "verbosity": "compact",
            "temperature_control": {"mode": "adaptive", "range": [0.2, 0.6]},
        },
        response_contract={
            "output_format": {
                "type": "object",
                "required_fields": [
                    "decision",
                    "confidence",
                    "summary",
                    "reasoning",
                    "compliance_tags",
                    "temperature_used",
                ],
                "on_failure": {
                    "action": "fallback",
                    "max_retries": 1,
                    "fallback": {
                        "decision": "unknown",
                        "confidence": "low",
                        "summary": "Recommendation rejected due to suspicious behaviour.",
                        "reasoning": "The model's decision was rejected because it changed a high confidence decision too quickly. This requires additional validation.",
                    },
                },
            },
            "max_response_time_ms": 1,
            "behaviour_signature": {"key": "decision", "expected_type": "string"},
        },
    )
    behavioural_contract_obj = BehaviouralContract(contract)

    def analyst_agent(signal: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        try:
            raise Exception("Test error")
        except Exception:
            # Always return fallback on error
            return cast(
                Dict[str, Any],
                contract["response_contract"]["output_format"]["on_failure"][
                    "fallback"
                ],
            )

    result = analyst_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert result["confidence"] == "low"
    assert not behavioural_contract_obj.is_suspicious_behavior(result)


def test_invalid_response_fallback():
    contract = behavioural_contract(
        version="1.1",
        description="Base behavioural contract for the Analyst Agent.",
        role="analyst",
        policy={
            "pii": False,
            "compliance_tags": ["EU-AI-ACT"],
            "allowed_tools": ["search", "summary", "confidence_estimator"],
        },
        behavioural_flags={
            "conservatism": "moderate",
            "verbosity": "compact",
            "temperature_control": {"mode": "adaptive", "range": [0.2, 0.6]},
        },
        response_contract={
            "output_format": {
                "type": "object",
                "required_fields": [
                    "decision",
                    "confidence",
                    "summary",
                    "reasoning",
                    "compliance_tags",
                    "temperature_used",
                ],
                "on_failure": {
                    "action": "fallback",
                    "max_retries": 1,
                    "fallback": {
                        "decision": "unknown",
                        "confidence": "low",
                        "summary": "Recommendation rejected due to suspicious behaviour.",
                        "reasoning": "The model's decision was rejected because it changed a high confidence decision too quickly. This requires additional validation.",
                    },
                },
            },
            "max_response_time_ms": 1,
            "behaviour_signature": {"key": "decision", "expected_type": "string"},
        },
    )

    behavioural_contract_obj = BehaviouralContract(contract)

    def test_agent(signal: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        response = {
            "decision": "BUY"
            # Missing required field: confidence
        }
        is_valid, fallback = _validate_response(response, contract)
        if not is_valid and fallback is not None:
            return fallback
        return response

    result = test_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert result["confidence"] == "low"
    assert not behavioural_contract_obj.is_suspicious_behavior(result)


def test_suspicious_behavior_detection():
    contract = behavioural_contract(
        version="1.1",
        description="Base behavioural contract for the Analyst Agent.",
        role="analyst",
        policy={
            "pii": False,
            "compliance_tags": ["EU-AI-ACT"],
            "allowed_tools": ["search", "summary", "confidence_estimator"],
        },
        behavioural_flags={
            "conservatism": "moderate",
            "verbosity": "compact",
            "temperature_control": {"mode": "adaptive", "range": [0.2, 0.6]},
        },
        response_contract={
            "output_format": {
                "type": "object",
                "required_fields": [
                    "decision",
                    "confidence",
                    "summary",
                    "reasoning",
                    "compliance_tags",
                    "temperature_used",
                ],
                "on_failure": {
                    "action": "fallback",
                    "max_retries": 1,
                    "fallback": {
                        "decision": "unknown",
                        "confidence": "low",
                        "summary": "Recommendation rejected due to suspicious behaviour.",
                        "reasoning": "The model's decision was rejected because it changed a high confidence decision too quickly. This requires additional validation.",
                    },
                },
            },
            "max_response_time_ms": 1,
            "behaviour_signature": {"key": "decision", "expected_type": "string"},
        },
    )

    behavioural_contract_obj = BehaviouralContract(contract)

    def test_agent(signal: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        response = {
            "decision": "APPROVE",
            "confidence": "high",
            "summary": "Strong approval signal",
            "reasoning": "Multiple factors support approval",
            "compliance_tags": ["EU-AI-ACT"],
            "temperature_used": 0.3,
        }
        is_valid, fallback = _validate_response(response, contract)
        if not is_valid and fallback is not None:
            return fallback
        if behavioural_contract_obj.is_suspicious_behavior(response, kwargs):
            response["flagged_for_review"] = True
            response["strike_reason"] = "High confidence decision changed unexpectedly"
        return response

    # Test high confidence change pattern
    result = test_agent(
        {"indicators": {"rsi": 50}},
        memory=[{"analysis": {"decision": "REJECT", "confidence": "high"}}],
        pattern_history=["REJECT", "REJECT", "REJECT"],  # Established pattern
    )
    assert result["flagged_for_review"] is True
    assert "strike_reason" in result
    assert behavioural_contract_obj.is_suspicious_behavior(
        result,
        {
            "memory": [{"analysis": {"decision": "REJECT", "confidence": "high"}}],
            "pattern_history": ["REJECT", "REJECT", "REJECT"],
        },
    )
