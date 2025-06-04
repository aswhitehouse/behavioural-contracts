# Behavioral Contracts

A Python package for enforcing behavioral contracts in AI agents. This package provides a decorator-based approach to ensure AI agents adhere to specified behavioral constraints, response formats, and performance requirements.

## Installation

```bash
pip install behavioral-contracts
```

## Quick Start

```python
from behavioral_contracts import behavioral_contract

# Define your contract specification
contract_spec = {
    "version": "1.0",
    "description": "Trading agent behavioral contract",
    "role": "trading_advisor",
    "behavioral_flags": {
        "temperature_control": {
            "mode": "adaptive",
            "range": [0.2, 0.6]
        }
    },
    "response_contract": {
        "output_format": {
            "required_fields": ["recommendation", "confidence", "reasoning"],
            "on_failure": {
                "max_retries": 2,
                "fallback": {
                    "recommendation": "HOLD",
                    "confidence": "low",
                    "reasoning": "Unable to provide recommendation"
                }
            },
            "max_response_time_ms": 5000
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

# Use the decorator on your AI agent function
@behavioral_contract(contract_spec)
def trading_advisor(signal: dict, temperature: float = 0.7):
    # Your AI agent logic here
    return {
        "recommendation": "BUY",
        "confidence": "high",
        "reasoning": "Strong bullish indicators"
    }
```

## Features

- **Behavioral Contract Enforcement**: Ensure AI agents adhere to specified behavioral constraints
- **Response Format Validation**: Validate response formats against required schemas
- **Temperature Control**: Adaptive or fixed temperature control for model outputs
- **Health Monitoring**: Track agent health and performance
- **Escalation Handling**: Define escalation paths for contract violations
- **Suspicious Behavior Detection**: Detect and flag suspicious changes in agent behavior

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run type checking
mypy behavioral_contracts

# Format code
black behavioral_contracts
isort behavioral_contracts
```

## License

MIT License 