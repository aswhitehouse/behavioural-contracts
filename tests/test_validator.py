import pytest
from behavioral_contracts.validator import ResponseValidator, try_parse_json

def test_required_fields_validation():
    validator = ResponseValidator(["recommendation", "confidence"])
    
    # Valid response
    assert validator.validate({
        "recommendation": "BUY",
        "confidence": "high"
    }) is True
    
    # Invalid response - missing field
    assert validator.validate({
        "recommendation": "BUY"
    }) is False
    
    # Invalid response - wrong type
    assert validator.validate({
        "recommendation": 123,  # Should be string
        "confidence": "high"
    }) is False

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