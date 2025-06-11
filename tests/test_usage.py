from behavioural_contracts import behavioural_contract

# Define a simple contract for a trading bot
TRADING_CONTRACT = {
    "version": "1.0",
    "description": "Trading bot contract",
    "role": "trading_agent",
    "behavioural_flags": {
        "temperature_control": {
            "mode": "fixed",
            "range": [0.2, 0.6]
        }
    },
    "response_contract": {
        "output_format": {
            "required_fields": ["action", "confidence", "reason"],
            "max_response_time_ms": 1000,
            "max_retries": 1,
            "on_failure": {
                "fallback": {
                    "action": "HOLD",
                    "confidence": "low",
                    "reason": "Fallback due to error"
                }
            }
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

@behavioural_contract(TRADING_CONTRACT)
def trading_bot(market_data: dict, **kwargs):
    # Simulate a trading bot that analyzes market data
    rsi = market_data.get("rsi", 50)
    
    if rsi < 30:
        return {
            "action": "BUY",
            "confidence": "high",
            "reason": "RSI indicates oversold conditions"
        }
    elif rsi > 70:
        return {
            "action": "SELL",
            "confidence": "high",
            "reason": "RSI indicates overbought conditions"
        }
    else:
        return {
            "action": "HOLD",
            "confidence": "medium",
            "reason": "RSI in neutral territory"
        }

# Test the trading bot
if __name__ == "__main__":
    # Test case 1: Oversold conditions
    result1 = trading_bot({"rsi": 25})
    print("\nTest 1 - Oversold conditions:")
    print(result1)
    
    # Test case 2: Overbought conditions
    result2 = trading_bot({"rsi": 75})
    print("\nTest 2 - Overbought conditions:")
    print(result2)
    
    # Test case 3: Invalid response (missing required field)
    @behavioural_contract(TRADING_CONTRACT)
    def invalid_bot(market_data: dict, **kwargs):
        return {"action": "BUY"}  # Missing required fields
    
    result3 = invalid_bot({"rsi": 50})
    print("\nTest 3 - Invalid response (should use fallback):")
    print(result3)
    
    # Test case 4: Invalid contract specification
    try:
        invalid_contract = {
            "version": "1.0",
            "response_contract": {
                "output_format": {
                    "required_fields": ["action", "confidence", "reason"],
                    "max_response_time_ms": "invalid"  # Should be an integer
                }
            }
        }
        @behavioural_contract(invalid_contract)
        def test_invalid_contract(market_data: dict, **kwargs):
            return {"action": "BUY", "confidence": "high", "reason": "test"}
    except Exception as e:
        print("\nTest 4 - Invalid contract specification:")
        print(f"Expected validation error: {str(e)}") 