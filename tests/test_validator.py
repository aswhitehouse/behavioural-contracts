from behavioral_contracts.validator import ResponseValidator, try_parse_json

def test_required_fields_validation():
    validator = ResponseValidator(["decision", "confidence"])
    dummy_policy = {}
    dummy_behavioral_flags = {"temperature_control": {"range": [0.2, 0.6]}}
    dummy_response_contract = {"max_response_time_ms": 1000}

    # Valid response
    assert validator.validate({
        "decision": "BUY",
        "confidence": "high"
    }, dummy_policy, dummy_behavioral_flags, dummy_response_contract) == (True, '')
    
    # Missing required field
    assert validator.validate({
        "decision": "BUY"
    }, dummy_policy, dummy_behavioral_flags, dummy_response_contract) == (False, 'missing required fields')
    
    # Invalid response - wrong type (should still pass as only presence is checked)
    assert validator.validate({
        "decision": 123,  # Should be string
        "confidence": "high"
    }, dummy_policy, dummy_behavioral_flags, dummy_response_contract) == (True, '')

def test_json_parsing():
    # Valid JSON string
    json_str = '{"recommendation": "BUY", "confidence": "high"}'
    parsed = try_parse_json(json_str)
    assert parsed is not None
    assert parsed["recommendation"] == "BUY"
    assert parsed["confidence"] == "high"
    
    # Invalid JSON string
    invalid_str = '{"recommendation": "BUY", "confidence": "high"'  # Missing closing brace
    assert try_parse_json(invalid_str) is None
    
    # Non-JSON string
    assert try_parse_json("not json") is None 