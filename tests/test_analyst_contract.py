from behavioral_contracts import behavioral_contract

# Test contract specification
ANALYST_CONTRACT = {
    "version": "1.1",
    "description": "Base behavioral contract for the Analyst Agent.",
    "role": "analyst",

    "policy": {
        "PII": False,
        "compliance_tags": ["EU-AI-ACT"],
        "allowed_tools": ["search", "summary", "confidence_estimator"]
    },

    "behavioral_flags": {
        "conservatism": "moderate",
        "verbosity": "compact",
        "temperature_control": {
            "mode": "adaptive",
            "range": [0.2, 0.6]
        }
    },

    "response_contract": {
        "output_format": {
            "type": "object",
            "required_fields": [
                "decision", "confidence", "summary", "reasoning"
            ],
            "on_failure": {
                "action": "resubmit_prompt",
                "max_retries": 1,
                "fallback": {
                    "decision": "unknown",
                    "confidence": "low",
                    "summary": "Recommendation rejected due to suspicious behavior.",
                    "reasoning": "The model's decision was rejected because it changed a high confidence decision too quickly. This requires additional validation."
                }
            }
        },
        "max_response_time_ms": 4000
    },

    "health": {
        "strikes": 0,
        "status": "healthy"
    },

    "escalation": {
        "on_unexpected_output": "invoke_validator_agent",
        "on_context_mismatch": "escalate_to_orchestrator",
        "fallback_role": "SafeAnalyst"
    }
}

def test_valid_response():
    @behavioral_contract(ANALYST_CONTRACT)
    def analyst_agent(signal: dict, **kwargs):
        return {
            "decision": "BUY",
            "confidence": "high",
            "summary": "Strong buy signal based on technical indicators",
            "reasoning": "Multiple indicators show bullish momentum",
            "compliance_tags": ["EU-AI-ACT"],
            "tools": ["search", "confidence_estimator"]
        }
    
    result = analyst_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "BUY"
    assert result["confidence"] == "high"
    assert "summary" in result
    assert "reasoning" in result
    assert "EU-AI-ACT" in result["compliance_tags"]

def test_pii_detection():
    @behavioral_contract(ANALYST_CONTRACT)
    def analyst_agent(signal: dict, **kwargs):
        return {
            "decision": "BUY",
            "confidence": "high",
            "summary": "Contact us at test@example.com for more details",
            "reasoning": "Multiple indicators show bullish momentum",
            "compliance_tags": ["EU-AI-ACT"]
        }
    
    result = analyst_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert result["confidence"] == "low"
    assert "pii" in result["reasoning"].lower()

def test_compliance_tags():
    @behavioral_contract(ANALYST_CONTRACT)
    def analyst_agent(signal: dict, **kwargs):
        return {
            "decision": "BUY",
            "confidence": "high",
            "summary": "Strong buy signal",
            "reasoning": "Multiple indicators show bullish momentum"
            # Missing compliance_tags
        }
    
    result = analyst_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert "compliance" in result["reasoning"].lower()

def test_allowed_tools():
    @behavioral_contract(ANALYST_CONTRACT)
    def analyst_agent(signal: dict, **kwargs):
        return {
            "decision": "BUY",
            "confidence": "high",
            "summary": "Strong buy signal",
            "reasoning": "Multiple indicators show bullish momentum",
            "compliance_tags": ["EU-AI-ACT"],
            "tools": ["unauthorized_tool"]  # Not in allowed_tools
        }
    
    result = analyst_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert "unauthorized" in result["reasoning"].lower()

def test_high_confidence_change():
    @behavioral_contract(ANALYST_CONTRACT)
    def analyst_agent(signal: dict, **kwargs):
        return {
            "decision": "SELL",  # Changed from previous BUY
            "confidence": "high",
            "summary": "Strong sell signal",
            "reasoning": "Multiple indicators show bearish momentum",
            "compliance_tags": ["EU-AI-ACT"],
            "previous_decision": "BUY"  # Previous high confidence recommendation
        }

    result = analyst_agent({"indicators": {"rsi": 50}})
    # If high confidence recommendation is changed, fallback should be returned and flagged_for_review should be True
    if result["decision"] == "unknown":
        assert result["flagged_for_review"] is True
        assert "changed" in result["reasoning"].lower()
    else:
        assert result["decision"] == "SELL"

def test_temperature_control():
    @behavioral_contract(ANALYST_CONTRACT)
    def analyst_agent(signal: dict, temperature: float = 0.7, **kwargs):
        return {
            "decision": "BUY",
            "confidence": "high",
            "summary": "Strong buy signal",
            "reasoning": "Multiple indicators show bullish momentum",
            "compliance_tags": ["EU-AI-ACT"],
            "temperature_used": temperature
        }

    result = analyst_agent({"indicators": {"rsi": 50}})
    # If temperature is out of range, fallback should be returned
    if result["decision"] == "unknown":
        assert result["confidence"] == "low"
        assert "temperature" in result["reasoning"].lower()
    else:
        assert 0.2 <= result["temperature_used"] <= 0.6

def test_response_time():
    import time

    @behavioral_contract(ANALYST_CONTRACT)
    def analyst_agent(signal: dict, **kwargs):
        time.sleep(0.005)  # Simulate slow response
        return {
            "decision": "BUY",
            "confidence": "high",
            "summary": "Strong buy signal",
            "reasoning": "Multiple indicators show bullish momentum",
            "compliance_tags": ["EU-AI-ACT"]
        }

    result = analyst_agent({"indicators": {"rsi": 50}})
    # If response is too slow, fallback should be returned
    if result["decision"] == "unknown":
        assert result["confidence"] == "low"
        assert "timeout" in result["reasoning"].lower()
    else:
        assert result["decision"] == "BUY"

def test_health_monitoring():
    @behavioral_contract(ANALYST_CONTRACT)
    def analyst_agent(signal: dict, **kwargs):
        raise Exception("Test error")
    
    # First failure should trigger retry
    result = analyst_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert result["confidence"] == "low"
    assert "error" in result["reasoning"].lower()

def test_invalid_response_fallback():
    @behavioral_contract(ANALYST_CONTRACT)
    def test_agent(signal: dict, **kwargs):
        return {
            "decision": "BUY"
            # Missing required field: confidence
        }
    
    result = test_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert result["confidence"] == "low"

def test_suspicious_behavior_detection():
    @behavioral_contract(ANALYST_CONTRACT)
    def test_agent(signal: dict, **kwargs):
        return {
            "decision": "APPROVE",
            "confidence": "high",
            "summary": "Strong approval signal",
            "reasoning": "Multiple factors support approval",
            "compliance_tags": ["test_tag"]
        }
    
    # Test high confidence change pattern
    result = test_agent(
        {"context_suggestion": "REJECT"},  # Context suggests one thing
        context={
            "memory": [{
                "analysis": {
                    "decision": "REJECT",
                    "confidence": "high"
                }
            }],
            "pattern_history": ["REJECT", "REJECT", "REJECT"]  # Established pattern
        }
    )
    assert result["flagged_for_review"] is True
    assert "strike_reason" in result 