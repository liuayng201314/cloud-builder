"""ANSI code handling utilities."""

import re
from typing import Dict, Any


def strip_ansi_codes(text: str) -> str:
    """
    Remove ANSI escape codes from text.
    
    Args:
        text: Text that may contain ANSI escape codes
    
    Returns:
        Text with ANSI escape codes removed
    """
    if not text:
        return text
    # Remove ANSI escape sequences (more comprehensive pattern)
    # Pattern matches: \x1B[...m, \x1B[K, etc.
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    cleaned = ansi_escape.sub('', str(text))
    # Also remove any remaining escape sequences that might have been missed
    cleaned = re.sub(r'\x1B\[[0-9;]*m', '', cleaned)  # Color codes
    cleaned = re.sub(r'\x1B\[[0-9;]*K', '', cleaned)  # Erase codes
    cleaned = re.sub(r'\x1B\[[0-9;]*[HJ]', '', cleaned)  # Cursor codes
    return cleaned


def clean_dict_for_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively clean all string values in a dictionary to remove ANSI codes.
    This ensures all data returned to MCP is JSON-safe.
    
    Args:
        data: Dictionary that may contain ANSI codes in string values
    
    Returns:
        Dictionary with all string values cleaned
    """
    cleaned = {}
    for key, value in data.items():
        if isinstance(value, str):
            cleaned[key] = strip_ansi_codes(value)
        elif isinstance(value, dict):
            cleaned[key] = clean_dict_for_json(value)
        elif isinstance(value, list):
            cleaned[key] = [
                clean_dict_for_json(item) if isinstance(item, dict) else
                strip_ansi_codes(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            cleaned[key] = value
    return cleaned

