# Behavioral Contracts

A Python package for enforcing behavioral contracts in AI agents. This package provides a framework for defining, validating, and enforcing behavioral contracts that ensure AI agents operate within specified constraints and patterns.

## Installation

```bash
pip install behavioral-contracts
```

## Quick Start

```python
from behavioral_contracts import behavioral_contract, generate_contract

# Define your contract
contract_data = {
    "version": "1.1",
    "description": "Financial Analyst Agent",
    "role": "analyst",
    "memory": {
        "enabled": True,
        "format": "string",
        "usage": "prompt-append",
        "required": True,
        "description": "Market analysis context"
    },
    "policy": {
        "pii": False,
        "compliance_tags": ["EU-AI-ACT"],
        "allowed_tools": ["search", "summary"]
    },
    "behavioral_flags": {
        "conservatism": "moderate",
        "verbosity": "compact",
        "temperature_control": {
            "mode": "adaptive",
            "range": [0.2, 0.6]
        }
    }
}

# Generate a formatted contract
contract = generate_contract(contract_data)

# Use the contract with your agent
@behavioral_contract(contract)
def analyst_agent(signal: dict, **kwargs):
    return {
        "decision": "BUY",
        "confidence": "high",
        "summary": "Strong buy signal based on technical indicators",
        "reasoning": "Multiple indicators show bullish momentum",
        "compliance_tags": ["EU-AI-ACT"]
    }
```

## Key Features

### 1. Contract Generation

Generate properly formatted contracts from specification data:

```python
from behavioral_contracts import generate_contract

# Basic contract
basic_contract = generate_contract({
    "version": "1.1",
    "description": "Simple Agent",
    "role": "agent"
})

# Contract with memory settings
memory_contract = generate_contract({
    "version": "1.1",
    "description": "Memory-Enabled Agent",
    "role": "agent",
    "memory": {
        "enabled": True,
        "format": "string",
        "usage": "prompt-append",
        "required": True
    }
})

# Contract with policy
policy_contract = generate_contract({
    "version": "1.1",
    "description": "Compliant Agent",
    "role": "agent",
    "policy": {
        "pii": False,
        "compliance_tags": ["GDPR", "HIPAA"],
        "allowed_tools": ["search", "analyze"]
    }
})
```

### 2. Contract Formatting

Format existing contracts to ensure proper value types:

```python
from behavioral_contracts import format_contract

# Format a contract with mixed types
formatted = format_contract({
    "version": 1.1,  # Will be converted to string
    "description": "My Agent",
    "memory": {
        "enabled": True,  # Will be converted to "true"
        "required": 1  # Will be converted to "true"
    }
})
```

### 3. Behavioral Contract Decorator

Use the decorator to enforce contracts on your agent functions:

```python
from behavioral_contracts import behavioral_contract

# Using a dictionary
@behavioral_contract({
    "version": "1.1",
    "description": "Trading Agent",
    "role": "trader",
    "policy": {
        "pii": False,
        "compliance_tags": ["FINRA"]
    }
})
def trading_agent(signal: dict, **kwargs):
    return {
        "decision": "BUY",
        "confidence": "high",
        "compliance_tags": ["FINRA"]
    }

# Using a generated contract
contract = generate_contract({
    "version": "1.1",
    "description": "Analysis Agent",
    "role": "analyst"
})

@behavioral_contract(contract)
def analysis_agent(signal: dict, **kwargs):
    return {
        "decision": "ANALYZE",
        "confidence": "high"
    }
```

### 4. Memory and Context Handling

The contract system handles memory and context for suspicious behavior detection:

```python
@behavioral_contract({
    "version": "1.1",
    "description": "Context-Aware Agent",
    "role": "agent",
    "memory": {
        "enabled": True,
        "required": True
    }
})
def context_agent(signal: dict, **kwargs):
    # The contract will automatically check for suspicious behavior
    # based on the provided context and memory
    return {
        "decision": "APPROVE",
        "confidence": "high"
    }

# Use with context
result = context_agent(
    signal={},
    context={
        "memory": [{
            "analysis": {
                "decision": "REJECT",
                "confidence": "high"
            }
        }],
        "pattern_history": ["REJECT", "REJECT", "REJECT"]
    }
)
```

## Contract Structure

A behavioral contract consists of several key sections:

1. **Basic Information**
   - `version`: Contract version
   - `description`: Agent description
   - `role`: Agent role

2. **Memory Configuration**
   - `enabled`: Whether memory is enabled
   - `format`: Memory format
   - `usage`: How memory is used
   - `required`: Whether memory is required
   - `description`: Memory description

3. **Policy Settings**
   - `pii`: PII handling flag
   - `compliance_tags`: Required compliance tags
   - `allowed_tools`: List of allowed tools

4. **Behavioral Flags**
   - `conservatism`: Agent conservatism level
   - `verbosity`: Output verbosity
   - `temperature_control`: Temperature settings

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 