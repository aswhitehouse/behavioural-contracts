import json

from behavioural_contracts.generator import format_contract, generate_contract


def test_generate_contract_basic():
    spec_data = {
        "version": "1.1",
        "description": "Test agent",
        "role": "test",
        "memory": {
            "enabled": True,
            "format": "string",
            "usage": "prompt-append",
            "required": True,
            "description": "Test context",
        },
    }

    result = generate_contract(spec_data)
    parsed = json.loads(result)

    assert parsed["version"] == "1.1"
    assert parsed["description"] == "Test agent"
    assert parsed["role"] == "test"
    assert parsed["memory"]["enabled"] is True
    assert parsed["memory"]["format"] == "string"
    assert parsed["memory"]["usage"] == "prompt-append"
    assert parsed["memory"]["required"] is True
    assert parsed["memory"]["description"] == "Test context"


def test_generate_contract_with_policy():
    spec_data = {
        "version": "1.1",
        "description": "Test agent",
        "role": "test",
        "policy": {
            "pii": False,
            "compliance_tags": ["TEST-TAG"],
            "allowed_tools": ["test_tool"],
        },
    }

    result = generate_contract(spec_data)
    parsed = json.loads(result)

    assert parsed["policy"]["pii"] is False
    assert parsed["policy"]["compliance_tags"] == ["TEST-TAG"]
    assert parsed["policy"]["allowed_tools"] == ["test_tool"]


def test_generate_contract_with_behavioural_flags():
    spec_data = {
        "version": "1.1",
        "description": "Test agent",
        "role": "test",
        "behavioural_flags": {
            "conservatism": "moderate",
            "verbosity": "compact",
            "temperature_control": {"mode": "adaptive", "range": [0.2, 0.6]},
        },
    }

    result = generate_contract(spec_data)
    parsed = json.loads(result)

    assert parsed["behavioural_flags"]["conservatism"] == "moderate"
    assert parsed["behavioural_flags"]["verbosity"] == "compact"
    assert parsed["behavioural_flags"]["temperature_control"]["mode"] == "adaptive"
    assert parsed["behavioural_flags"]["temperature_control"]["range"] == [0.2, 0.6]


def test_format_contract():
    contract = {
        "version": 1.1,
        "description": "Test agent",
        "role": "test",
        "memory": {
            "enabled": True,
            "format": "string",
            "usage": "prompt-append",
            "required": True,
            "description": "Test context",
        },
    }

    result = format_contract(contract)
    parsed = json.loads(result)

    assert isinstance(parsed["version"], str)
    assert parsed["version"] == "1.1"
    assert parsed["memory"]["enabled"] is True
    assert parsed["memory"]["required"] is True


def test_generate_contract_defaults():
    spec_data = {"version": "1.1", "description": "Test agent", "role": "test"}

    result = generate_contract(spec_data)
    parsed = json.loads(result)

    assert parsed["memory"]["enabled"] is False
    assert parsed["memory"]["format"] == "string"
    assert parsed["memory"]["usage"] == "prompt-append"
    assert parsed["memory"]["required"] is False
    assert parsed["memory"]["description"] == ""


def test_generate_contract_with_mixed_types():
    spec_data = {
        "version": 1.1,
        "description": "Test agent",
        "role": "test",
        "memory": {
            "enabled": "true",
            "format": "string",
            "usage": "prompt-append",
            "required": 1,
            "description": "Test context",
        },
        "policy": {
            "pii": "false",
            "compliance_tags": ["TEST-TAG"],
            "allowed_tools": ["test_tool"],
        },
    }

    result = generate_contract(spec_data)
    parsed = json.loads(result)

    assert isinstance(parsed["version"], str)
    assert parsed["version"] == "1.1"
    assert parsed["memory"]["enabled"] == "true"
    assert parsed["memory"]["required"] == 1
    assert parsed["policy"]["pii"] == "false"
