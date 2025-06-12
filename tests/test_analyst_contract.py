from behavioural_contracts import behavioural_contract

# Test contract specification
ANALYST_CONTRACT = {
    "version": "1.1",
    "description": "Base behavioural contract for the Analyst Agent.",
    "role": "analyst",
    "policy": {
        "pii": False,
        "compliance_tags": ["EU-AI-ACT"],
        "allowed_tools": ["search", "summary", "confidence_estimator"]
    },
    "behavioural_flags": {
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
                "decision", "confidence", "summary", "reasoning", "compliance_tags", "temperature_used"
            ],
            "on_failure": {
                "action": "fallback",
                "max_retries": 1,
                "fallback": {
                    "decision": "unknown",
                    "confidence": "low",
                    "summary": "Recommendation rejected due to suspicious behaviour.",
                    "reasoning": "The model's decision was rejected because it changed a high confidence decision too quickly. This requires additional validation."
                }
            }
        },
        "max_response_time_ms": 1,
        "behaviour_signature": {
            "key": "decision",
            "expected_type": "string"
        }
    },
    "health": {
        "strikes": 0,
        "status": "healthy"
    },
    "escalation": {
        "on_unexpected_output": "flag_for_review",
        "on_context_mismatch": "flag_for_review",
        "fallback_role": "SafeAnalyst"
    }
}

def test_valid_response():
    @behavioural_contract(ANALYST_CONTRACT)
    def analyst_agent(signal: dict, **kwargs):
        return {
            "decision": "BUY",
            "confidence": "high",
            "summary": "Strong buy signal based on technical indicators",
            "reasoning": "Multiple indicators show bullish momentum",
            "compliance_tags": ["EU-AI-ACT"],
            "tools": ["search", "confidence_estimator"],
            "temperature_used": 0.3
        }
    
    result = analyst_agent({"indicators": {"rsi": 50}})
    print(f'result: {result}')
    assert result["decision"] == "BUY"
    assert result["confidence"] == "high"
    assert "summary" in result
    assert "reasoning" in result
    assert "EU-AI-ACT" in result["compliance_tags"]

def test_pii_detection():
    @behavioural_contract(ANALYST_CONTRACT)
    def analyst_agent(signal: dict, **kwargs):
        return {
            "decision": "BUY",
            "confidence": "high",
            "summary": "Contact us at test@example.com for more details",
            "reasoning": "Multiple indicators show bullish momentum",
            "compliance_tags": ["EU-AI-ACT"],
            "temperature_used": 0.3
        }
    
    result = analyst_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert result["confidence"] == "low"
    assert "pii" in result["reasoning"].lower()

def test_compliance_tags():
    @behavioural_contract(ANALYST_CONTRACT)
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
    @behavioural_contract(ANALYST_CONTRACT)
    def analyst_agent(signal: dict, **kwargs):
        return {
            "decision": "BUY",
            "confidence": "high",
            "summary": "Strong buy signal",
            "reasoning": "Multiple indicators show bullish momentum",
            "compliance_tags": ["EU-AI-ACT"],
            "tools": ["unauthorized_tool"],  # Not in allowed_tools
            "temperature_used": 0.3
        }
    
    result = analyst_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert "unauthorized" in result["reasoning"].lower()

def test_high_confidence_change():
    @behavioural_contract(ANALYST_CONTRACT)
    def analyst_agent(signal: dict, **kwargs):
        return {
            "decision": "SELL",  # Changed from previous BUY
            "confidence": "high",
            "summary": "Strong sell signal",
            "reasoning": "Multiple indicators show bearish momentum",
            "compliance_tags": ["EU-AI-ACT"],
            "temperature_used": 0.3
        }

    # Test with memory containing previous high confidence decision
    result = analyst_agent(
        {"indicators": {"rsi": 50}},
        memory=[{
            "analysis": {
                "decision": "BUY",
                "confidence": "high"
            }
        }]
    )
    assert result["flagged_for_review"] is True
    assert "strike_reason" in result

def test_temperature_control():
    @behavioural_contract(ANALYST_CONTRACT)
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
    assert result["decision"] == "unknown"
    assert result["confidence"] == "low"
    assert "temperature" in result["reasoning"].lower()

def test_response_time():
    import time

    @behavioural_contract(ANALYST_CONTRACT)
    def analyst_agent(signal: dict, **kwargs):
        time.sleep(0.005)  # Simulate slow response
        return {
            "decision": "BUY",
            "confidence": "high",
            "summary": "Strong buy signal",
            "reasoning": "Multiple indicators show bullish momentum",
            "compliance_tags": ["EU-AI-ACT"],
            "temperature_used": 0.3
        }

    result = analyst_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert result["confidence"] == "low"
    assert "timeout" in result["reasoning"].lower()

def test_health_monitoring():
    @behavioural_contract(ANALYST_CONTRACT)
    def analyst_agent(signal: dict, **kwargs):
        raise Exception("Test error")
    
    result = analyst_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert result["confidence"] == "low"
    assert "error" in result["reasoning"].lower()

def test_invalid_response_fallback():
    @behavioural_contract(ANALYST_CONTRACT)
    def test_agent(signal: dict, **kwargs):
        return {
            "decision": "BUY"
            # Missing required field: confidence
        }
    
    result = test_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert result["confidence"] == "low"

def test_suspicious_behavior_detection():
    @behavioural_contract(ANALYST_CONTRACT)
    def test_agent(signal: dict, **kwargs):
        return {
            "decision": "APPROVE",
            "confidence": "high",
            "summary": "Strong approval signal",
            "reasoning": "Multiple factors support approval",
            "compliance_tags": ["EU-AI-ACT"],
            "temperature_used": 0.3
        }
    
    # Test high confidence change pattern
    result = test_agent(
        {"indicators": {"rsi": 50}},
        memory=[{
            "analysis": {
                "decision": "REJECT",
                "confidence": "high"
            }
        }],
        pattern_history=["REJECT", "REJECT", "REJECT"]  # Established pattern
    )
    assert result["flagged_for_review"] is True
    assert "strike_reason" in result 