from behavioural_contracts import behavioural_contract

# Sample contract specification for testing
TEST_CONTRACT = {
    "version": "1.0",
    "description": "Test contract",
    "role": "test_agent",
    "policy": {
        "pii": False,
        "compliance_tags": ["test_tag"],
        "allowed_tools": ["test_tool"]
    },
    "behavioural_flags": {
        "temperature_control": {
            "mode": "fixed",
            "range": [0.2, 0.6]
        },
        "conservatism": "medium",
        "verbosity": "medium"
    },
    "response_contract": {
        "output_format": {
            "required_fields": ["decision", "confidence"],
            "on_failure": {
                "action": "fallback",
                "max_retries": 1,
                "fallback": {
                    "decision": "unknown",
                    "confidence": "low",
                    "reason": "Fallback due to error"
                }
            },
            "max_response_time_ms": 1000
        },
        "max_response_time_ms": 1000,
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
        "on_invalid_response": "fallback",
        "on_context_mismatch": "flag_for_review",
        "fallback_role": "test_agent"
    }
}

def test_valid_response():
    @behavioural_contract(TEST_CONTRACT)
    def test_agent(signal: dict, **kwargs):
        return {
            "decision": "BUY",
            "confidence": "high",
            "compliance_tags": ["test_tag"]
        }
    
    result = test_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "BUY"
    assert result["confidence"] == "high"

def test_invalid_response_fallback():
    @behavioural_contract(TEST_CONTRACT)
    def test_agent(signal: dict, **kwargs):
        return {
            "decision": "BUY"
            # Missing required field: confidence
        }
    
    result = test_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert result["confidence"] == "low"

def test_suspicious_behavior_detection():
    @behavioural_contract(TEST_CONTRACT)
    def test_agent(signal: dict, **kwargs):
        return {
            "decision": "BUY",
            "confidence": "high",
            "compliance_tags": ["test_tag"]
        }
    
    # Test with memory containing previous high confidence decision
    result = test_agent(
        {"indicators": {"rsi": 50}},
        memory=[{
            "analysis": {
                "decision": "SELL",
                "confidence": "high"
            }
        }]
    )
    assert result["flagged_for_review"] is True
    assert "strike_reason" in result

def test_temperature_control():
    @behavioural_contract(TEST_CONTRACT)
    def test_agent(signal: dict, temperature: float = 0.3, **kwargs):
        return {
            "decision": "BUY",
            "confidence": "high",
            "temperature_used": temperature,
            "compliance_tags": ["test_tag"]
        }
    
    result = test_agent({"indicators": {"rsi": 50}})
    assert 0.2 <= result["temperature_used"] <= 0.6

def test_health_monitoring():
    @behavioural_contract(TEST_CONTRACT)
    def test_agent(signal: dict, **kwargs):
        raise Exception("Test error")
    
    result = test_agent({"indicators": {"rsi": 50}})
    assert result["decision"] == "unknown"
    assert result["confidence"] == "low"

def test_behavior_signature():
    # Create a contract that tracks 'goal' instead of 'decision'
    goal_contract = TEST_CONTRACT.copy()
    goal_contract["response_contract"]["behaviour_signature"] = {
        "key": "goal",
        "expected_type": "string"
    }
    goal_contract["response_contract"]["output_format"]["required_fields"] = ["goal", "confidence"]

    @behavioural_contract(goal_contract)
    def test_agent(signal: dict, **kwargs):
        return {
            "goal": "APPROVE",
            "confidence": "high",
            "compliance_tags": ["test_tag"]
        }
    
    # Test high confidence change with goal instead of decision
    result = test_agent(
        {"indicators": {"rsi": 50}},
        memory=[{
            "analysis": {
                "goal": "REJECT",
                "confidence": "high"
            }
        }]
    )
    assert result["flagged_for_review"] is True
    assert "strike_reason" in result 