"""MCP tools for remote command execution."""

from typing import Optional, Dict, Any

from log_config.logging_config import get_logger
from utils.ansi_utils import strip_ansi_codes, clean_dict_for_json
from utils.error_utils import return_error
from ssh.ssh_client import get_ssh_client

logger = get_logger("CloudBuilder.CommandTools")


def execute_remote_command(
    command: str,
    working_directory: Optional[str],
    host: str,
    port: int,
    username: str,
    password: str
) -> Dict[str, Any]:
    """
    Execute a command on the remote server via SSH.
    
    Args:
        command: Command to execute on the remote server
        working_directory: Optional working directory for the command
        host: SSH server hostname
        port: SSH server port
        username: SSH username
        password: SSH password
    
    Returns:
        Dictionary with command output, exit code, and any errors
    """
    logger.info(f"Executing remote command: {command}" + (f" (working_directory: {working_directory})" if working_directory else ""))
    
    try:
        ssh_client = get_ssh_client(host, port, username, password)
        
        # Prepare command with working directory if specified
        full_command = command
        if working_directory:
            full_command = f"cd {working_directory} && {command}"
        
        logger.info(f"Executing SSH command: {full_command}")
        
        # Execute command
        stdin, stdout, stderr = ssh_client.exec_command(full_command)
        
        # Get results
        exit_code = stdout.channel.recv_exit_status()
        stdout_content = stdout.read().decode('utf-8')
        stderr_content = stderr.read().decode('utf-8')
        
        ssh_client.close()
        logger.debug("SSH connection closed")
        
        logger.info(f"Command executed: exit_code={exit_code}, stdout_length={len(stdout_content)}, stderr_length={len(stderr_content)}")
        if exit_code != 0:
            logger.warning(f"Command exited with non-zero code: {exit_code}, stderr: {stderr_content}")
        
        # Clean stdout and stderr to remove any ANSI codes
        stdout_content = strip_ansi_codes(stdout_content) if stdout_content else ""
        stderr_content = strip_ansi_codes(stderr_content) if stderr_content else ""
        
        result_dict = {
            "success": True,
            "command": full_command,
            "exit_code": exit_code,
            "stdout": stdout_content,
            "stderr": stderr_content,
            "working_directory": working_directory
        }
        # Clean all string values to ensure JSON safety
        return clean_dict_for_json(result_dict)
        
    except Exception as e:
        error_msg = f"Command execution failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return return_error(error_msg)

