import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def try_parse_json(raw_content: Any) -> Optional[Dict]:
    """Helper function to parse JSON content with various formats."""
    if isinstance(raw_content, dict):
        return raw_content

    if not isinstance(raw_content, str):
        return None

    raw_content = raw_content.strip()

    # Handle markdown code blocks
    if raw_content.startswith("```") and raw_content.endswith("```"):
        content_lines = raw_content.split("\n")
        if len(content_lines) > 2:
            content = "\n".join(content_lines[1:-1])
            content = content.replace("```", "").strip()
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return None

    try:
        return json.loads(raw_content)
    except json.JSONDecodeError:
        return None

class ResponseValidator:
    def __init__(self, required_fields: List[str]):
        self.required_fields = required_fields
        logger.info(f"ResponseValidator initialized with required fields: {required_fields}")

    def validate(self, response: Any) -> bool:
        logger.info("Validating response...")
        # First try to parse if it's a string
        if isinstance(response, str):
            logger.debug("Response is string, attempting to parse JSON")
            parsed = try_parse_json(response)
            if parsed is None:
                logger.error("Failed to parse response as JSON")
                return False
            response = parsed

        if not isinstance(response, dict):
            logger.error(f"Response is not a dictionary: {type(response)}")
            return False

        # Check if all required fields are present and have correct types
        for field in self.required_fields:
            if field not in response:
                logger.error(f"Missing required field: {field}")
                return False
            if not isinstance(response[field], str):
                logger.error(f"Field {field} is not a string: {type(response[field])}")
                return False

        logger.info("Response validation passed")
        return True