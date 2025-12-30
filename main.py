#!/usr/bin/env python3
"""
CloudBuilder MCP Server

A Model Context Protocol server that provides CloudBuilder operations including:
- Directory synchronization
- Single file upload
- File reading
- Remote command execution

This server uses stdio transport for secure local communication.
"""

from typing import Optional, Dict, Any
from fastmcp import FastMCP

# Import logging configuration
from log_config.logging_config import setup_logging, get_logger
# Import configuration
from config.config_loader import load_config
# Import MCP tools
from mcp_tools.sync_tools import sync_directory as sync_directory_impl
from mcp_tools.file_tools import upload_file as upload_file_impl, read_remote_file as read_remote_file_impl, \
    list_remote_directory as list_remote_directory_impl
from mcp_tools.command_tools import execute_remote_command as execute_remote_command_impl
# Import MCP resources and prompts
from mcp_resources.resources import get_cloudbuilder_config
from mcp_resources.prompts import (
    check_config_workflow as _check_config_workflow,
    sync_workflow as _sync_workflow,
    build_workflow as _build_workflow,
    sync_and_build_workflow as _sync_and_build_workflow
)

# Setup logging
setup_logging()
logger = get_logger("CloudBuilder")

# Load configuration
config = load_config()

# Create FastMCP server instance
mcp = FastMCP("CloudBuilder")


@mcp.tool()
def sync_directory(local_dir: Optional[str] = None, remote_dir: Optional[str] = None,
                   delete_excess: bool = True) -> Dict[str, Any]:
    """
    Synchronize a local directory to remote server.
    
    Args:
        local_dir: Local directory path (defaults to LOCAL_PATH env var)
        remote_dir: Remote directory path (defaults to REMOTE_PATH env var)
        delete_excess: Delete files in destination that don't exist in source (default: True)
    
    Returns:
        Dictionary with sync results including statistics and any errors
    """
    return sync_directory_impl(
        local_dir,
        remote_dir,
        delete_excess,
        config.REMOTE_HOST_NAME,
        config.LOCAL_PATH,
        config.REMOTE_PATH,
        config.RCLONE_EXE_PATH
    )


@mcp.tool()
def upload_file(local_file_path: str, remote_file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Upload a file to remote server.
    
    Args:
        local_file_path: Path to local file. Use absolute path (recommended) or relative path (will be resolved relative to LOCAL_PATH).
        remote_file_path: Remote destination path (optional, auto-determined from LOCAL_PATH/REMOTE_PATH mapping)
    
    Returns:
        Dictionary with upload result
    """
    return upload_file_impl(
        local_file_path,
        remote_file_path,
        config.REMOTE_HOST_NAME,
        config.LOCAL_PATH,
        config.REMOTE_PATH,
        config.RCLONE_EXE_PATH
    )


@mcp.tool()
def read_remote_file(remote_file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    Read the contents of a file from the remote server.
    
    Args:
        remote_file_path: Path to the remote file to read
        encoding: Text encoding to use (default: utf-8)
    
    Returns:
        Dictionary with file contents or error
    """
    return read_remote_file_impl(
        remote_file_path,
        encoding,
        config.REMOTE_HOST_NAME,
        config.RCLONE_EXE_PATH
    )


@mcp.tool()
def execute_remote_command(command: str, working_directory: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a command on the remote server via SSH.
    
    Args:
        command: Command to execute on the remote server
        working_directory: Optional working directory for the command
    
    Returns:
        Dictionary with command output, exit code, and any errors
    """
    return execute_remote_command_impl(
        command,
        working_directory,
        config.TARGET_HOST,
        config.TARGET_PORT,
        config.TARGET_USERNAME,
        config.TARGET_PASSWORD
    )


@mcp.tool()
def list_remote_directory(remote_dir_path: str) -> Dict[str, Any]:
    """
    List contents of a remote directory.
    
    Args:
        remote_dir_path: Path to the remote directory to list
    
    Returns:
        Dictionary with directory contents
    """
    return list_remote_directory_impl(
        remote_dir_path,
        config.REMOTE_HOST_NAME,
        config.RCLONE_EXE_PATH
    )


@mcp.resource("cloudbuilder://config")
def get_config_resource() -> str:
    """
    Get current cloudbuilder server configuration (without sensitive data).
    """
    return get_cloudbuilder_config(config)


@mcp.prompt()
def check_config_workflow() -> str:
    """
    A workflow prompt for checking cloudbuilder configuration.
    """
    return _check_config_workflow()


@mcp.prompt()
def sync_workflow() -> str:
    """
    A workflow prompt for synchronizing files to remote server.
    """
    return _sync_workflow(config)


@mcp.prompt()
def build_workflow() -> str:
    """
    A workflow prompt for building/compiling on remote server with error fixing capability.
    """
    return _build_workflow(config)


@mcp.prompt()
def sync_and_build_workflow() -> str:
    """
    A workflow prompt for synchronizing files and then building on remote server with error fixing capability.
    """
    return _sync_and_build_workflow(config)


# Update tool docstrings with actual configuration values
def _update_tool_docs():
    """Update tool docstrings with actual configuration values."""
    if config.LOCAL_PATH and config.REMOTE_PATH:
        path_mapping = f"LOCAL_PATH: {config.LOCAL_PATH} -> REMOTE_PATH: {config.REMOTE_PATH}"
    else:
        path_mapping = "LOCAL_PATH/REMOTE_PATH not configured"

    # Update upload_file docstring
    if upload_file.__doc__:
        upload_file.__doc__ = upload_file.__doc__.rstrip() + f"\n\nPath mapping: {path_mapping}"

    # Update sync_directory docstring
    if sync_directory.__doc__:
        defaults = f"LOCAL_PATH: {config.LOCAL_PATH or 'not configured'}, REMOTE_PATH: {config.REMOTE_PATH or 'not configured'}"
        sync_directory.__doc__ = sync_directory.__doc__.rstrip() + f"\n\nDefaults: {defaults}"


# Update tool docstrings with configuration values
_update_tool_docs()


def main():
    """Main entry point for the MCP server."""
    logger.info("Starting CloudBuilder MCP Server")
    logger.debug(
        f"Configuration: host={config.TARGET_HOST}, port={config.TARGET_PORT}, username={config.TARGET_USERNAME}, "
        f"local_path={config.LOCAL_PATH}, remote_path={config.REMOTE_PATH}, build_command={config.BUILD_COMMAND}")

    # Run the MCP server using stdio transport
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
