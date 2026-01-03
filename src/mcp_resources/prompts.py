"""MCP workflow prompts."""

from config.config_loader import Config


def check_config_workflow() -> str:
    """
    A workflow prompt for checking cloudbuilder configuration.
    """
    return """Check the current CloudBuilder configuration:

1. Retrieve configuration using cloudbuilder://config resource
2. Report:
   - Connection status (configured/incomplete)
   - Remote server (host, port, username)
   - Paths (local_path, remote_path)
   - Build command (if configured)
   - Missing or incomplete settings"""


def sync_workflow(config: Config) -> str:
    """
    A workflow prompt for synchronizing files to remote server.
    
    Args:
        config: Configuration instance
    """
    local_path = config.LOCAL_PATH or "LOCAL_PATH"
    remote_path = config.REMOTE_PATH or "REMOTE_PATH"
    
    return f"""Synchronize files to remote server:

1. Use sync_directory tool (omit parameters to use defaults, or provide full paths: local_dir="{local_path}", remote_dir="{remote_path}")
2. Check sync result for errors"""


def build_workflow(config: Config) -> str:
    """
    A workflow prompt for building/compiling on remote server with error fixing capability.
    
    Args:
        config: Configuration instance
    """
    if not config.BUILD_COMMAND:
        return """Build on remote server:

1. Inform user that BUILD_COMMAND must be configured in .cloudbuilder.json or environment variable
2. BUILD_COMMAND is required before building"""
    
    local_path = config.LOCAL_PATH or "LOCAL_PATH"
    remote_path = config.REMOTE_PATH or "REMOTE_PATH"
    
    return f"""Build the project on remote server and automatically fix compilation errors:

1. Run build command "{config.BUILD_COMMAND}" in remote directory "{remote_path}" using execute_remote_command tool.

2. If the build fails:
   - Read error messages from the command output
   - Find which files have errors (these paths are in REMOTE format: "{remote_path}/...")
   - Convert each REMOTE file path to LOCAL path by replacing "{remote_path}/" with "{local_path}/"
   - Open and fix the LOCAL files based on error messages
   - Upload the fixed files using sync_directory or upload_file tool
   - Run the build command again
   - Repeat this process up to 5 times until build succeeds

3. Report the final result: success or list any remaining errors after 5 attempts."""


def sync_and_build_workflow(config: Config) -> str:
    """
    A workflow prompt for synchronizing files and then building on remote server with error fixing capability.
    
    Args:
        config: Configuration instance
    """
    if not config.BUILD_COMMAND:
        return """Sync and build workflow:

1. Inform user that BUILD_COMMAND must be configured
2. Use sync_directory tool to synchronize files
3. Wait for sync to complete, then execute BUILD_COMMAND"""
    
    local_path = config.LOCAL_PATH or "LOCAL_PATH"
    remote_path = config.REMOTE_PATH or "REMOTE_PATH"
    
    return f"""Sync files to remote server, build the project, and automatically fix compilation errors:

1. Sync files using sync_directory (omit parameters or use full paths: local_dir="{local_path}", remote_dir="{remote_path}")

2. Run build command "{config.BUILD_COMMAND}" in remote directory "{remote_path}" using execute_remote_command tool.

3. If the build fails:
   - Read error messages from the command output
   - Find which files have errors (these paths are in REMOTE format: "{remote_path}/...")
   - Convert each REMOTE file path to LOCAL path by replacing "{remote_path}/" with "{local_path}/"
   - Open and fix the LOCAL files based on error messages
   - Upload the fixed files using sync_directory or upload_file tool
   - Run the build command again
   - Repeat this process up to 5 times until build succeeds

4. Report the final result: success or list any remaining errors after 5 attempts."""

