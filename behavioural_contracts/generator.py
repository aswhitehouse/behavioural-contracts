import json
from typing import Any, Dict


def _convert_to_bool(value: Any) -> bool:
    """Convert a value to a boolean, handling string representations."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def generate_contract_dict(spec_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a contract dictionary from spec data, preserving types."""
    formatted = {
        "version": str(spec_data.get("version", "1.1")),
        "description": spec_data.get("description", ""),
        "role": spec_data.get("role", ""),
    }
    if "policy" in spec_data:
        formatted["policy"] = {
            "pii": _convert_to_bool(spec_data["policy"].get("pii", False)),
            "compliance_tags": spec_data["policy"].get("compliance_tags", []),
            "allowed_tools": spec_data["policy"].get("allowed_tools", []),
        }
    if "behavioural_flags" in spec_data:
        formatted["behavioural_flags"] = {
            "conservatism": spec_data["behavioural_flags"].get(
                "conservatism", "moderate"
            ),
            "verbosity": spec_data["behavioural_flags"].get("verbosity", "compact"),
            "temperature_control": {
                "mode": spec_data["behavioural_flags"]["temperature_control"].get(
                    "mode", "adaptive"
                ),
                "range": spec_data["behavioural_flags"]["temperature_control"].get(
                    "range", [0.2, 0.6]
                ),
            },
        }
    if "response_contract" in spec_data:
        formatted["response_contract"] = spec_data["response_contract"]
    return formatted


class PythonJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that uses Python's True/False instead of JSON's true/false."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, bool):
            return str(obj).lower()
        return super().default(obj)


def generate_contract(spec_data: Dict[str, Any]) -> str:
    """Generate a properly formatted behavioural contract decorator from spec data (as a string)."""
    formatted = generate_contract_dict(spec_data)
    decorator_parts = []
    decorator_parts.append(f'version="{formatted["version"]}",')
    decorator_parts.append(f'description="{formatted["description"]}",')
    decorator_parts.append(f'role="{formatted["role"]}",')
    if "policy" in formatted:
        policy_str = json.dumps(
            formatted["policy"], indent=4, cls=PythonJSONEncoder
        ).replace("\n", "\n    ")
        policy_str = policy_str.replace("true", "True").replace("false", "False")
        decorator_parts.append(f"policy={policy_str}")
    if "behavioural_flags" in formatted:
        flags_str = json.dumps(
            formatted["behavioural_flags"], indent=4, cls=PythonJSONEncoder
        ).replace("\n", "\n    ")
        flags_str = flags_str.replace("true", "True").replace("false", "False")
        decorator_parts.append(f",\n    behavioural_flags={flags_str}")
    if "response_contract" in formatted:
        contract_str = json.dumps(
            formatted["response_contract"], indent=4, cls=PythonJSONEncoder
        ).replace("\n", "\n    ")
        contract_str = contract_str.replace("true", "True").replace("false", "False")
        decorator_parts.append(f",\n    response_contract={contract_str}")
    decorator = "\n    ".join(decorator_parts)
    return decorator


def format_contract(contract: Dict[str, Any]) -> str:
    """Format an existing contract to ensure all values are properly typed (returns decorator string)."""
    return generate_contract(contract)
