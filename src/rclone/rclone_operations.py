"""Rclone operations for remote directory and file management."""

import os
from typing import Dict, Any

from log_config.logging_config import get_logger
from rclone.rclone_executor import execute_rclone_command

logger = get_logger("CloudBuilder.RcloneOperations")


def ensure_remote_directory_exists(
    remote_dir_path: str,
    remote_host_name: str,
    rclone_exe_path: str = None
) -> bool:
    """
    Check if remote directory exists, and create it if it doesn't exist.
    
    Args:
        remote_dir_path: Remote directory path to check/create
        remote_host_name: Remote host name
        rclone_exe_path: Path to rclone executable (optional)
    
    Returns:
        True if directory exists or was created successfully, False otherwise
    """
    if not remote_host_name:
        logger.error("REMOTE_HOST_NAME not set, cannot check/create remote directory")
        return False
    
    rclone_exe = rclone_exe_path or "rclone"
    remote_dest = f"{remote_host_name}:{remote_dir_path}"
    
    # First, try to list the directory to check if it exists
    logger.info(f"Checking if remote directory exists: {remote_dest}")
    check_cmd = [rclone_exe, "lsd", remote_dest]
    
    # Use execute_rclone_command for consistent execution and logging
    # Note: Command execution logging is handled by execute_rclone_command
    result = execute_rclone_command(
        check_cmd,
        "lsd (check directory)",
        remote_host_name,
        rclone_exe_path,
        timeout=60
    )
    
    if not result.get("success"):
        # Check if the error is specifically "directory not found"
        stderr_content = result.get("stderr", "") or ""
        exit_code = result.get("exit_code", -1)
        
        stderr_lower = stderr_content.lower()
        is_directory_not_found = any(keyword in stderr_lower for keyword in [
            "directory not found",
            "doesn't exist",
            "no such file",
            "not found"
        ])
        
        if not is_directory_not_found:
            # Error is not "directory not found", it's something else (permission, network, etc.)
            logger.error(f"Failed to check remote directory (exit_code={exit_code}): {stderr_content.strip() if stderr_content else 'Unknown error'}")
            return False
        
        # Directory doesn't exist, create it
        logger.info(f"Remote directory does not exist, creating: {remote_dest}")
        mkdir_cmd = [rclone_exe, "mkdir", remote_dest]
        
        # Note: Command execution logging is handled by execute_rclone_command
        mkdir_result = execute_rclone_command(
            mkdir_cmd,
            "mkdir (create directory)",
            remote_host_name,
            rclone_exe_path,
            timeout=60
        )
        
        if mkdir_result.get("success"):
            logger.info(f"Successfully created remote directory: {remote_dest}")
            return True
        else:
            mkdir_stderr_content = mkdir_result.get("stderr", "") or ""
            mkdir_stderr_lower = mkdir_stderr_content.lower()
            # If directory already exists (created by another process), that's okay
            if any(keyword in mkdir_stderr_lower for keyword in [
                "already exists",
                "file exists",
                "directory exists"
            ]):
                logger.info(f"Remote directory already exists (created by another process): {remote_dest}")
                return True
            else:
                logger.error(f"Failed to create remote directory: {mkdir_stderr_content.strip() if mkdir_stderr_content else 'Unknown error'}")
                return False
    else:
        # Directory exists
        logger.info(f"Remote directory already exists: {remote_dest}")
        return True

