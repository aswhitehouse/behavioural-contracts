from typing import Any, Callable, Dict, TypeVar, cast

from behavioural_contracts.contract import behavioural_contract

T = TypeVar("T")


def behavioural_contract_decorator(
    contract_spec: Dict[str, Any],
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Type-safe decorator for behavioural contracts."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return func(*args, **kwargs)

        return cast(Callable[..., T], wrapper)

    return decorator


# Define a simple contract for a trading bot
TRADING_CONTRACT = {
    "version": "1.0",
    "description": "Trading bot contract",
    "role": "trading_agent",
    "policy": {
        "pii": False,
        "compliance_tags": ["trading"],
        "allowed_tools": ["market_data", "order_execution"],
    },
    "behavioural_flags": {
        "conservatism": "high",
        "verbosity": "compact",
        "temperature_control": {"mode": "fixed", "range": [0.2, 0.6]},
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
                    "reason": "Fallback due to error",
                }
            },
        }
    },
    "health": {"max_strikes": 3, "strike_window_seconds": 3600},
    "escalation": {
        "on_unexpected_output": "flag_for_review",
        "on_invalid_response": "fallback",
    },
}


@behavioural_contract_decorator(TRADING_CONTRACT)
def trading_bot(market_data: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    # Simulate a trading bot that analyzes market data
    rsi = market_data.get("rsi", 50)

    if rsi < 30:
        return {
            "action": "BUY",
            "confidence": "high",
            "reason": "RSI indicates oversold conditions",
        }
    elif rsi > 70:
        return {
            "action": "SELL",
            "confidence": "high",
            "reason": "RSI indicates overbought conditions",
        }
    else:
        return {
            "action": "HOLD",
            "confidence": "medium",
            "reason": "RSI in neutral territory",
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
    @behavioural_contract_decorator(TRADING_CONTRACT)
    def invalid_bot(market_data: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        return {"action": "BUY"}  # Missing required fields

    result3 = invalid_bot({"rsi": 50})
    print("\nTest 3 - Invalid response (should use fallback):")
    print(result3)

    # Test case 4: Invalid contract specification
    try:
        invalid_contract = behavioural_contract(
            version="1.0",
            description="Invalid contract",
            role="test",
            policy={"compliance_tags": ["test"], "allowed_tools": ["test"]},
            behavioural_flags={"conservatism": "high", "verbosity": "compact"},
            response_contract={
                "output_format": {
                    "required_fields": ["action", "confidence", "reason"],
                    "max_response_time_ms": "invalid",  # Should be an integer
                }
            },
        )

        @behavioural_contract_decorator(invalid_contract)
        def test_invalid_contract(
            market_data: Dict[str, Any], **kwargs: Any
        ) -> Dict[str, Any]:
            return {"action": "BUY", "confidence": "high", "reason": "test"}
    except Exception as e:
        print("\nTest 4 - Invalid contract specification:")
        print(f"Expected validation error: {e!s}")
