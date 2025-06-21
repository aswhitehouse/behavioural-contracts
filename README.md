# Behavioural Contracts

A Python package for enforcing behavioural contracts in AI agents. This package provides a framework for defining, validating, and enforcing behavioural contracts that ensure AI agents operate within specified constraints and patterns.

## Installation

```bash
pip install behavioural-contracts
```

## Quick Start

```python
from behavioural_contracts import behavioural_contract, generate_contract

# Define your contract
contract_data = {
    "version": "1.1",
    "description": "Financial Analyst Agent",
    "role": "analyst",
    "policy": {
        "pii": False,
        "compliance_tags": ["EU-AI-ACT"],
        "allowed_tools": ["search", "summary"]
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
                "decision", "confidence", "summary", "reasoning",
                "compliance_tags", "temperature_used"
            ],
            "on_failure": {
                "action": "fallback",
                "max_retries": 1,
                "fallback": {
                    "decision": "unknown",
                    "confidence": "low",
                    "summary": "Recommendation rejected due to validation failure.",
                    "reasoning": "The model's response failed validation checks."
                }
            }
        },
        "max_response_time_ms": 4000,
        "behaviour_signature": {
            "key": "decision",
            "expected_type": "string"
        }
    }
}

# Generate a formatted contract
contract = generate_contract(contract_data)

# Use the contract with your agent
@behavioural_contract(contract)
def analyst_agent(signal: dict, **kwargs):
    return {
        "decision": "BUY",
        "confidence": "high",
        "summary": "Strong buy signal based on technical indicators",
        "reasoning": "Multiple indicators show bullish momentum",
        "compliance_tags": ["EU-AI-ACT"],
        "temperature_used": 0.3  # Required field for temperature validation
    }
```

## Key Features

### 1. Contract Generation

Generate properly formatted contracts from specification data:

```python
from behavioural_contracts import generate_contract

# Basic contract
basic_contract = generate_contract({
    "version": "1.1",
    "description": "Simple Agent",
    "role": "agent",
    "response_contract": {
        "output_format": {
            "required_fields": ["decision", "confidence", "temperature_used"]
        }
    }
})

# Contract with policy and response validation
policy_contract = generate_contract({
    "version": "1.1",
    "description": "Compliant Agent",
    "role": "agent",
    "policy": {
        "pii": False,
        "compliance_tags": ["GDPR", "HIPAA"],
        "allowed_tools": ["search", "analyze"]
    },
    "response_contract": {
        "output_format": {
            "required_fields": [
                "decision", "confidence", "compliance_tags", "temperature_used"
            ]
        },
        "max_response_time_ms": 2000
    }
})
```

### 2. Contract Formatting

Format existing contracts to ensure proper value types:

```python
from behavioural_contracts import format_contract

# Format a contract with mixed types
formatted = format_contract({
    "version": 1.1,  # Will be converted to string
    "description": "My Agent",
    "response_contract": {
        "output_format": {
            "required_fields": ["decision", "temperature_used"]
        },
        "max_response_time_ms": 1000
    }
})
```

### 3. Behavioural Contract Decorator

Use the decorator to enforce contracts on your agent functions:

```python
from behavioural_contracts import behavioural_contract

# Using a dictionary
@behavioural_contract({
    "version": "1.1",
    "description": "Trading Agent",
    "role": "trader",
    "policy": {
        "pii": False,
        "compliance_tags": ["FINRA"]
    },
    "response_contract": {
        "output_format": {
            "required_fields": [
                "decision", "confidence", "compliance_tags", "temperature_used"
            ]
        }
    }
})
def trading_agent(signal: dict, **kwargs):
    return {
        "decision": "BUY",
        "confidence": "high",
        "compliance_tags": ["FINRA"],
        "temperature_used": 0.3
    }
```

### 4. Response Validation

The contract system enforces response validation including:
- Required fields
- Temperature range validation
- Response time limits
- Compliance tag verification
- PII detection
- Tool usage validation

```python
@behavioural_contract({
    "version": "1.1",
    "description": "Validated Agent",
    "role": "agent",
    "behavioural_flags": {
        "temperature_control": {
            "range": [0.2, 0.6]
        }
    },
    "response_contract": {
        "output_format": {
            "required_fields": [
                "decision", "confidence", "temperature_used"
            ]
        },
        "max_response_time_ms": 1000
    }
})
def validated_agent(signal: dict, **kwargs):
    # Response will be validated for:
    # - All required fields present
    # - Temperature within range
    # - Response time under 1000ms
    return {
        "decision": "APPROVE",
        "confidence": "high",
        "temperature_used": 0.3
    }
```

## Contract Structure

A behavioural contract consists of several key sections:

1. **Basic Information**
   - `version`: Contract version
   - `description`: Agent description
   - `role`: Agent role

2. **Policy Settings**
   - `pii`: PII handling flag
   - `compliance_tags`: Required compliance tags
   - `allowed_tools`: List of allowed tools

3. **Behavioural Flags**
   - `conservatism`: Agent conservatism level
   - `verbosity`: Output verbosity
   - `temperature_control`: Temperature settings
     - `mode`: Control mode (fixed/adaptive)
     - `range`: Allowed temperature range [min, max]

4. **Response Contract**
   - `output_format`: Response structure requirements
     - `type`: Output type (usually "object")
     - `required_fields`: List of required fields
     - `on_failure`: Fallback configuration
   - `max_response_time_ms`: Maximum allowed response time
   - `behaviour_signature`: Key field to track for suspicious behavior

## Python Installation
[![PyPI version](https://img.shields.io/pypi/v/behavioural-contracts)](https://pypi.org/project/behavioural-contracts/)
[![Python versions](https://img.shields.io/pypi/pyversions/behavioural-contracts)](https://pypi.org/project/behavioural-contracts/)
[![License](https://img.shields.io/pypi/l/behavioural-contracts)](https://pypi.org/project/behavioural-contracts/)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Overview
https://www.openagentstack.ai
