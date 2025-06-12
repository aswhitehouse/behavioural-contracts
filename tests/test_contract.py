import pytest

from behavioural_contracts.contract import behavioural_contract, validate_contract
from behavioural_contracts.exceptions import BehaviouralContractViolationError


def test_valid_contract():
    contract = behavioural_contract(
        version="1.0",
        description="Test contract",
        role="test_agent",
        policy={
            "pii": False,
            "compliance_tags": ["test"],
            "allowed_tools": ["test_tool"],
        },
        behavioural_flags={
            "conservatism": "high",
            "verbosity": "compact",
            "temperature_control": {"mode": "fixed", "range": [0.2, 0.6]},
        },
        response_contract={
            "output_format": {
                "required_fields": ["action", "confidence", "reason"],
                "max_response_time_ms": 1000,
            }
        },
    )
    validate_contract(contract)


def test_missing_version():
    contract = behavioural_contract(
        version="",
        description="Test contract",
        role="test_agent",
        policy={
            "pii": False,
            "compliance_tags": ["test"],
            "allowed_tools": ["test_tool"],
        },
        behavioural_flags={
            "conservatism": "high",
            "verbosity": "compact",
        },
        response_contract={
            "output_format": {
                "required_fields": ["action", "confidence", "reason"],
            }
        },
    )
    with pytest.raises(BehaviouralContractViolationError):
        validate_contract(contract)


def test_missing_description():
    contract = behavioural_contract(
        version="1.0",
        description="",
        role="test_agent",
        policy={
            "pii": False,
            "compliance_tags": ["test"],
            "allowed_tools": ["test_tool"],
        },
        behavioural_flags={
            "conservatism": "high",
            "verbosity": "compact",
        },
        response_contract={
            "output_format": {
                "required_fields": ["action", "confidence", "reason"],
            }
        },
    )
    with pytest.raises(BehaviouralContractViolationError):
        validate_contract(contract)


def test_missing_role():
    contract = behavioural_contract(
        version="1.0",
        description="Test contract",
        role="",
        policy={
            "pii": False,
            "compliance_tags": ["test"],
            "allowed_tools": ["test_tool"],
        },
        behavioural_flags={
            "conservatism": "high",
            "verbosity": "compact",
        },
        response_contract={
            "output_format": {
                "required_fields": ["action", "confidence", "reason"],
            }
        },
    )
    with pytest.raises(BehaviouralContractViolationError):
        validate_contract(contract)


def test_missing_compliance_tags():
    contract = behavioural_contract(
        version="1.0",
        description="Test contract",
        role="test_agent",
        policy={
            "pii": False,
            "compliance_tags": [],
            "allowed_tools": ["test_tool"],
        },
        behavioural_flags={
            "conservatism": "high",
            "verbosity": "compact",
        },
        response_contract={
            "output_format": {
                "required_fields": ["action", "confidence", "reason"],
            }
        },
    )
    with pytest.raises(BehaviouralContractViolationError):
        validate_contract(contract)


def test_missing_allowed_tools():
    contract = behavioural_contract(
        version="1.0",
        description="Test contract",
        role="test_agent",
        policy={
            "pii": False,
            "compliance_tags": ["test"],
            "allowed_tools": [],
        },
        behavioural_flags={
            "conservatism": "high",
            "verbosity": "compact",
        },
        response_contract={
            "output_format": {
                "required_fields": ["action", "confidence", "reason"],
            }
        },
    )
    with pytest.raises(BehaviouralContractViolationError):
        validate_contract(contract)


def test_missing_conservatism():
    contract = behavioural_contract(
        version="1.0",
        description="Test contract",
        role="test_agent",
        policy={
            "pii": False,
            "compliance_tags": ["test"],
            "allowed_tools": ["test_tool"],
        },
        behavioural_flags={
            "verbosity": "compact",
        },
        response_contract={
            "output_format": {
                "required_fields": ["action", "confidence", "reason"],
            }
        },
    )
    with pytest.raises(BehaviouralContractViolationError):
        validate_contract(contract)


def test_missing_verbosity():
    contract = behavioural_contract(
        version="1.0",
        description="Test contract",
        role="test_agent",
        policy={
            "pii": False,
            "compliance_tags": ["test"],
            "allowed_tools": ["test_tool"],
        },
        behavioural_flags={
            "conservatism": "high",
        },
        response_contract={
            "output_format": {
                "required_fields": ["action", "confidence", "reason"],
            }
        },
    )
    with pytest.raises(BehaviouralContractViolationError):
        validate_contract(contract)
