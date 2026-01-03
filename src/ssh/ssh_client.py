"""SSH client for remote command execution."""

import paramiko
from log_config.logging_config import get_logger

logger = get_logger("CloudBuilder.SSH")


def get_ssh_client(host: str, port: int, username: str, password: str):
    """
    Create and return an SSH client connection.
    
    Args:
        host: SSH server hostname
        port: SSH server port
        username: SSH username
        password: SSH password
    
    Returns:
        Connected SSH client
    
    Raises:
        ValueError: If required parameters are missing
        Exception: If connection fails
    """
    if not all([host, username, password]):
        logger.error("Missing required SSH connection parameters: host, username, or password")
        raise ValueError("Missing required SSH connection parameters")
    
    logger.info(f"Connecting to SSH server: {username}@{host}:{port}")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=15
        )
        logger.info(f"Successfully connected to SSH server: {host}:{port}")
        return ssh
    except Exception as e:
        logger.error(f"Failed to connect to SSH server {host}:{port}: {str(e)}")
        raise

