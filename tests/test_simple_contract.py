from typing import Any, Dict

import pytest

from behavioural_contracts.contract import behavioural_contract, validate_contract
from behavioural_contracts.exceptions import BehaviouralContractViolationError


def test_simple_contract_creation():
    """Test creating a simple behavioural contract with minimal fields."""
    # Create the contract specification as a dictionary
    contract_spec: Dict[str, Any] = {
        "version": "0.1.2",
        "description": "Simple chat response",
        "role": "chat_agent",
        "behavioural_flags": {"conservatism": "moderate", "verbosity": "compact"},
        "response_contract": {"output_format": {"required_fields": ["response"]}},
    }

    # Validate the contract
    validate_contract(contract_spec)

    # Check that all required fields are present
    assert contract_spec["version"] == "0.1.2"
    assert contract_spec["description"] == "Simple chat response"
    assert contract_spec["role"] == "chat_agent"

    # Check optional fields
    behavioural_flags = contract_spec["behavioural_flags"]
    assert isinstance(behavioural_flags, dict)
    assert behavioural_flags["conservatism"] == "moderate"
    assert behavioural_flags["verbosity"] == "compact"

    response_contract = contract_spec["response_contract"]
    assert isinstance(response_contract, dict)
    output_format = response_contract["output_format"]
    assert isinstance(output_format, dict)
    required_fields = output_format["required_fields"]
    assert isinstance(required_fields, list)
    assert required_fields == ["response"]


def test_minimal_contract_creation():
    """Test creating a contract with only the required fields."""
    # Create the contract specification as a dictionary
    contract_spec = {
        "version": "0.1.2",
        "description": "Simple chat response",
        "role": "chat_agent",
    }

    # Validate the contract
    validate_contract(contract_spec)

    # Check that only required fields are present
    assert contract_spec["version"] == "0.1.2"
    assert contract_spec["description"] == "Simple chat response"
    assert contract_spec["role"] == "chat_agent"

    # Check that optional fields are not present
    assert "behavioural_flags" not in contract_spec
    assert "response_contract" not in contract_spec
    assert "policy" not in contract_spec


def test_missing_required_fields():
    """Test that missing required fields raise appropriate errors."""

    # Missing version
    with pytest.raises(
        BehaviouralContractViolationError, match="Contract version is required"
    ):
        contract_spec = {"description": "Simple chat response", "role": "chat_agent"}
        validate_contract(contract_spec)

    # Missing description
    with pytest.raises(
        BehaviouralContractViolationError, match="Contract description is required"
    ):
        contract_spec = {"version": "0.1.2", "role": "chat_agent"}
        validate_contract(contract_spec)

    # Missing role
    with pytest.raises(
        BehaviouralContractViolationError, match="Contract role is required"
    ):
        contract_spec = {"version": "0.1.2", "description": "Simple chat response"}
        validate_contract(contract_spec)


def test_invalid_field_types():
    """Test that invalid field types raise appropriate errors."""

    # behavioural_flags not a dict
    with pytest.raises(
        BehaviouralContractViolationError,
        match="behavioural_flags must be a dictionary",
    ):
        contract_spec = {
            "version": "0.1.2",
            "description": "Simple chat response",
            "role": "chat_agent",
            "behavioural_flags": "not a dict",
        }
        validate_contract(contract_spec)

    # response_contract not a dict
    with pytest.raises(
        BehaviouralContractViolationError,
        match="response_contract must be a dictionary",
    ):
        contract_spec = {
            "version": "0.1.2",
            "description": "Simple chat response",
            "role": "chat_agent",
            "response_contract": "not a dict",
        }
        validate_contract(contract_spec)


def test_contract_decorator_usage():
    """Test using the behavioural_contract as a decorator."""

    @behavioural_contract(
        version="0.1.2",
        description="Simple chat response",
        role="chat_agent",
        behavioural_flags={"conservatism": "moderate", "verbosity": "compact"},
        response_contract={"output_format": {"required_fields": ["response"]}},
    )
    def chat_agent(message: str) -> dict:
        return {"response": f"Hello! You said: {message}"}

    # Test the decorated function
    result = chat_agent("test message")
    assert result["response"] == "Hello! You said: test message"


def test_contract_decorator_with_invalid_response():
    """Test that the decorator handles invalid responses correctly."""

    @behavioural_contract(
        version="0.1.2",
        description="Simple chat response",
        role="chat_agent",
        response_contract={"output_format": {"required_fields": ["response"]}},
    )
    def chat_agent(message: str) -> dict:
        # Return a response without the required 'response' field
        return {"message": f"Hello! You said: {message}"}

    # Test the decorated function - should return fallback
    result = chat_agent("test message")
    assert "response" in result
    assert result["response"] == ""  # Fallback value
    assert "reasoning" in result
    assert "error" in result


def test_contract_decorator_with_empty_response():
    """Test that the decorator handles empty responses correctly."""

    @behavioural_contract(
        version="0.1.2", description="Simple chat response", role="chat_agent"
    )
    def chat_agent(message: str) -> dict:
        # Return an empty response
        return {}

    # Test the decorated function - should return fallback
    result = chat_agent("test message")
    assert "response" in result
    assert result["response"] == ""  # Fallback value
    assert "reasoning" in result
    assert "error" in result
