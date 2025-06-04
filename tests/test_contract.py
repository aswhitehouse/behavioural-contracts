import pytest
from behavioral_contracts import behavioral_contract, BehavioralContractViolation

# Sample contract specification for testing
TEST_CONTRACT = {
    "version": "1.0",
    "description": "Test contract",
    "role": "test_agent",
    "behavioral_flags": {
        "temperature_control": {
            "mode": "fixed",
            "range": [0.2, 0.6]
        }
    },
    "response_contract": {
        "output_format": {
            "required_fields": ["recommendation", "confidence"],
            "on_failure": {
                "max_retries": 1,
                "fallback": {
                    "recommendation": "HOLD",
                    "confidence": "low"
                }
            },
            "max_response_time_ms": 1000
        }
    },
    "health": {
        "max_strikes": 3,
        "strike_window_seconds": 3600
    },
    "escalation": {
        "on_unexpected_output": "flag_for_review",
        "on_invalid_response": "fallback"
    }
}

def test_valid_response():
    @behavioral_contract(TEST_CONTRACT)
    def test_agent(signal: dict, **kwargs):
        return {
            "recommendation": "BUY",
            "confidence": "high"
        }
    
    result = test_agent({"indicators": {"rsi": 50}})
    assert result["recommendation"] == "BUY"
    assert result["confidence"] == "high"

def test_invalid_response_fallback():
    @behavioral_contract(TEST_CONTRACT)
    def test_agent(signal: dict, **kwargs):
        return {
            "recommendation": "BUY"
            # Missing required field: confidence
        }
    
    result = test_agent({"indicators": {"rsi": 50}})
    assert result["recommendation"] == "HOLD"
    assert result["confidence"] == "low"

def test_suspicious_behavior_detection():
    @behavioral_contract(TEST_CONTRACT)
    def test_agent(signal: dict, **kwargs):
        return {
            "recommendation": "BUY",
            "confidence": "high"
        }
    
    # Simulate memory with previous high confidence recommendation
    result = test_agent(
        {},
        memory=[{
            "analysis": {
                "recommendation": "SELL",
                "confidence": "high"
            }
        }],
        indicators={
            "rsi": 20,
            "ema_50": 100,
            "ema_200": 200,
            "trend": "strong_downtrend"
        }
    )
    assert result["flagged_for_review"] is True
    assert "strike_reason" in result

def test_temperature_control():
    @behavioral_contract(TEST_CONTRACT)
    def test_agent(signal: dict, temperature: float = 0.7, **kwargs):
        return {
            "recommendation": "BUY",
            "confidence": "high",
            "temperature_used": temperature
        }
    
    result = test_agent({"indicators": {"rsi": 50}})
    assert 0.2 <= result["temperature_used"] <= 0.6

def test_health_monitoring():
    @behavioral_contract(TEST_CONTRACT)
    def test_agent(signal: dict, **kwargs):
        raise Exception("Test error")
    
    # First failure should trigger retry
    result = test_agent({"indicators": {"rsi": 50}})
    assert result["recommendation"] == "HOLD"
    assert result["confidence"] == "low" 