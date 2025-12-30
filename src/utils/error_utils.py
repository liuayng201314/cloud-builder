"""Error handling utilities."""

from typing import Dict, Any
from .ansi_utils import strip_ansi_codes, clean_dict_for_json


def return_error(error_msg: str, **kwargs) -> Dict[str, Any]:
    """
    Return an error dictionary with cleaned error message.
    This ensures all error messages are JSON-safe.
    
    Args:
        error_msg: Error message (will be cleaned of ANSI codes)
        **kwargs: Additional fields to include in the error response
    
    Returns:
        Dictionary with cleaned error message
    """
    cleaned_msg = strip_ansi_codes(error_msg)
    result = {"error": cleaned_msg}
    result.update(kwargs)
    return clean_dict_for_json(result)

