import json
from behavioural_contracts.generator import generate_contract, format_contract

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
            "description": "Test context"
        }
    }
    
    result = generate_contract(spec_data)
    parsed = json.loads(result)
    
    assert parsed["version"] == "1.1"
    assert parsed["description"] == "Test agent"
    assert parsed["role"] == "test"
    assert parsed["memory"]["enabled"] == "true"
    assert parsed["memory"]["format"] == "string"
    assert parsed["memory"]["usage"] == "prompt-append"
    assert parsed["memory"]["required"] == "true"
    assert parsed["memory"]["description"] == "Test context"

def test_generate_contract_with_policy():
    spec_data = {
        "version": "1.1",
        "description": "Test agent",
        "role": "test",
        "policy": {
            "pii": False,
            "compliance_tags": ["TEST-TAG"],
            "allowed_tools": ["test_tool"]
        }
    }
    
    result = generate_contract(spec_data)
    parsed = json.loads(result)
    
    assert parsed["policy"]["pii"] == "false"
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
            "temperature_control": {
                "mode": "adaptive",
                "range": [0.2, 0.6]
            }
        }
    }
    
    result = generate_contract(spec_data)
    parsed = json.loads(result)
    
    assert parsed["behavioural_flags"]["conservatism"] == "moderate"
    assert parsed["behavioural_flags"]["verbosity"] == "compact"
    assert parsed["behavioural_flags"]["temperature_control"]["mode"] == "adaptive"
    assert parsed["behavioural_flags"]["temperature_control"]["range"] == [0.2, 0.6]

def test_format_contract():
    contract = {
        "version": 1.1,  # Should be converted to string
        "description": "Test agent",
        "role": "test",
        "memory": {
            "enabled": True,  # Should be converted to "true"
            "format": "string",
            "usage": "prompt-append",
            "required": True,  # Should be converted to "true"
            "description": "Test context"
        }
    }
    
    result = format_contract(contract)
    parsed = json.loads(result)
    
    assert parsed["version"] == "1.1"
    assert parsed["memory"]["enabled"] == "true"
    assert parsed["memory"]["required"] == "true"

def test_generate_contract_defaults():
    spec_data = {
        "version": "1.1",
        "description": "Test agent",
        "role": "test"
    }
    
    result = generate_contract(spec_data)
    parsed = json.loads(result)
    
    # Check default values
    assert parsed["memory"]["enabled"] == "false"
    assert parsed["memory"]["format"] == "string"
    assert parsed["memory"]["usage"] == "prompt-append"
    assert parsed["memory"]["required"] == "false"
    assert parsed["memory"]["description"] == "" 