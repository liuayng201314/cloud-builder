"""MCP resources."""

import json
from config.config_loader import Config


def get_cloudbuilder_config(config: Config) -> str:
    """
    Get current cloudbuilder server configuration (without sensitive data).
    
    Args:
        config: Configuration instance
    
    Returns:
        JSON string with configuration
    """
    config_dict = {
        "host": config.TARGET_HOST,
        "port": config.TARGET_PORT,
        "username": config.TARGET_USERNAME,
        "local_path": config.LOCAL_PATH,
        "remote_path": config.REMOTE_PATH,
        "build_command": config.BUILD_COMMAND,
        "filter_rules_file": ".sync_rules",
        "connection_status": "configured" if all([config.TARGET_HOST, config.TARGET_USERNAME, config.TARGET_PASSWORD]) else "incomplete"
    }
    return json.dumps(config_dict, indent=2)

