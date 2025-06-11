import json
from typing import Dict, Any, Union

def generate_contract(spec_data: Dict[str, Any]) -> str:
    """Generate a properly formatted behavioral contract from spec data.
    
    Args:
        spec_data: Dictionary containing contract configuration
        
    Returns:
        str: JSON string of the formatted contract
        
    Example input:
    {
        "version": "1.1",
        "description": "Financial analyst agent",
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
    """
    # Format all values as strings
    formatted = {
        "version": str(spec_data.get("version", "1.1")),
        "description": str(spec_data.get("description", "")),
        "role": str(spec_data.get("role", "")),
        "memory": {
            "enabled": str(spec_data.get("memory", {}).get("enabled", False)).lower(),
            "format": str(spec_data.get("memory", {}).get("format", "string")),
            "usage": str(spec_data.get("memory", {}).get("usage", "prompt-append")),
            "required": str(spec_data.get("memory", {}).get("required", False)).lower(),
            "description": str(spec_data.get("memory", {}).get("description", ""))
        }
    }
    
    # Add policy if present
    if "policy" in spec_data:
        formatted["policy"] = {
            "pii": str(spec_data["policy"].get("pii", False)).lower(),
            "compliance_tags": [str(tag) for tag in spec_data["policy"].get("compliance_tags", [])],
            "allowed_tools": [str(tool) for tool in spec_data["policy"].get("allowed_tools", [])]
        }
    
    # Add behavioral flags if present
    if "behavioral_flags" in spec_data:
        formatted["behavioral_flags"] = {
            "conservatism": str(spec_data["behavioral_flags"].get("conservatism", "moderate")),
            "verbosity": str(spec_data["behavioral_flags"].get("verbosity", "compact")),
            "temperature_control": {
                "mode": str(spec_data["behavioral_flags"]["temperature_control"].get("mode", "adaptive")),
                "range": [float(x) for x in spec_data["behavioral_flags"]["temperature_control"].get("range", [0.2, 0.6])]
            }
        }
    
    return json.dumps(formatted)

def format_contract(contract: Dict[str, Any]) -> str:
    """Format an existing contract to ensure all values are properly typed.
    
    This is useful for formatting contracts that are already in the correct structure
    but may have incorrect value types.
    
    Args:
        contract: Dictionary containing the contract
        
    Returns:
        str: JSON string of the formatted contract
    """
    return generate_contract(contract) 