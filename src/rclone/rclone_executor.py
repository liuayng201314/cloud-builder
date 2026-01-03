"""Rclone command executor."""

import os
import sys
import subprocess
from typing import Dict, Any, List

from log_config.logging_config import get_logger
from utils.ansi_utils import strip_ansi_codes

logger = get_logger("CloudBuilder.Rclone")


def get_rclone_env() -> Dict[str, str]:
    """
    Get environment variables for rclone to disable color output.
    
    Returns:
        Dictionary of environment variables
    """
    env = os.environ.copy()
    # Disable color output via environment variable
    env['NO_COLOR'] = '1'
    env['RCLONE_COLOR'] = 'never'
    # Also set TERM to dumb to prevent color output
    env['TERM'] = 'dumb'
    # Disable any color-related environment variables
    env.pop('COLORTERM', None)
    return env


def diagnose_mcp_environment():
    """
    Diagnose MCP environment differences that might affect subprocess execution.
    This helps identify why subprocess might behave differently in MCP vs normal environment.
    """
    diagnostics = {
        "stdin_isatty": sys.stdin.isatty() if hasattr(sys.stdin, 'isatty') else None,
        "stdout_isatty": sys.stdout.isatty() if hasattr(sys.stdout, 'isatty') else None,
        "stderr_isatty": sys.stderr.isatty() if hasattr(sys.stderr, 'isatty') else None,
        "stdin_type": type(sys.stdin).__name__,
        "stdout_type": type(sys.stdout).__name__,
        "stderr_type": type(sys.stderr).__name__,
        "working_directory": os.getcwd(),
        "python_executable": sys.executable,
        "platform": sys.platform,
        "has_TERM": 'TERM' in os.environ,
        "TERM_value": os.environ.get('TERM'),
        "has_COLORTERM": 'COLORTERM' in os.environ,
        "COLORTERM_value": os.environ.get('COLORTERM'),
    }
    return diagnostics


def execute_rclone_command(
    cmd: List[str],
    description: str,
    remote_host_name: str,
    rclone_exe_path: str = None,
    timeout: int = 30,
    binary: bool = False
) -> Dict[str, Any]:
    """
    Execute a rclone command and return the result.
    
    Args:
        cmd: Command list to execute (should already include rclone executable)
        description: Description of the operation for logging
        remote_host_name: Remote host name (required for validation)
        rclone_exe_path: Path to rclone executable (defaults to "rclone" if not specified)
        timeout: Timeout in seconds (default: 30)
        binary: If True, return stdout as bytes instead of text (default: False)
    
    Returns:
        Dictionary with success status, stdout (bytes if binary=True, str otherwise), stderr, and exit_code
    """
    if not remote_host_name:
        error_msg = f"REMOTE_HOST_NAME environment variable must be set to use rclone {description}"
        logger.error(error_msg)
        return {"error": error_msg, "success": False}
    
    # Validate rclone executable
    rclone_exe = rclone_exe_path or "rclone"
    if rclone_exe_path and not os.path.exists(rclone_exe_path):
        error_msg = f"RCLONE_EXE_PATH specified but file does not exist: {rclone_exe_path}"
        logger.error(error_msg)
        return {"error": error_msg, "success": False}
    
    # Ensure the first element of cmd is the rclone executable
    # This is important for Windows compatibility
    if cmd and cmd[0] != rclone_exe:
        # If cmd doesn't start with rclone_exe, prepend it
        if not cmd[0].endswith('rclone') and not cmd[0].endswith('rclone.exe'):
            logger.warning(f"Command doesn't start with rclone executable, expected: {rclone_exe}, got: {cmd[0] if cmd else 'empty'}")
    
    # Note: We don't add --no-color flag as it's not supported in all rclone versions
    # Instead, we use environment variables and strip ANSI codes from output
    logger.info(f"Executing rclone command: {' '.join(cmd)}")
    
    # Get environment variables
    rclone_env = get_rclone_env()
    logger.debug(f"Using environment: NO_COLOR={rclone_env.get('NO_COLOR')}, RCLONE_COLOR={rclone_env.get('RCLONE_COLOR')}, TERM={rclone_env.get('TERM')}")
    
    # Log MCP environment diagnostics (only once per session, or on first error)
    if not hasattr(execute_rclone_command, '_diagnostics_logged'):
        diagnostics = diagnose_mcp_environment()
        logger.debug(f"MCP Environment Diagnostics: {diagnostics}")
        execute_rclone_command._diagnostics_logged = True
    
    try:
        # On Windows, subprocess.run with PIPE can hang even with communicate()
        # Use Popen with communicate() and explicit timeout handling
        logger.debug(f"Starting process with timeout={timeout}s")
        
        # Log the full command for debugging
        logger.debug(f"Full command: {cmd}")
        logger.debug(f"Working directory: {os.getcwd()}")
        
        # In MCP environment, stdin/stdout/stderr may be redirected
        # This can cause buffering issues on Windows
        # Solution: Explicitly set stdin to DEVNULL to avoid any interaction
        # For Windows, use line buffering (bufsize=1) for text mode to balance performance and reliability
        # bufsize=0 (unbuffered) can cause performance issues, bufsize=1 (line buffered) is better for text
        process = None
        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,  # Explicitly set stdin to avoid any interaction
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=not binary,  # Use text mode only if not binary
                encoding='utf-8' if not binary else None,
                errors='replace' if not binary else None,
                env=rclone_env,
                cwd=None,  # Use current working directory
                bufsize=1 if sys.platform == 'win32' and not binary else 0  # Line buffered on Windows for text, unbuffered for binary
            )
            
            # Use communicate() with timeout - this is the most reliable method
            # communicate() will read all output and wait for process to complete
            stdout_data, stderr_data = process.communicate(timeout=timeout)
            returncode = process.returncode
            
            # Convert to appropriate types
            if binary:
                stdout_bytes = stdout_data if isinstance(stdout_data, bytes) else stdout_data.encode('utf-8', errors='replace')
                stderr_str = stderr_data.decode('utf-8', errors='replace') if isinstance(stderr_data, bytes) else stderr_data
            else:
                stdout_str = stdout_data if isinstance(stdout_data, str) else stdout_data.decode('utf-8', errors='replace')
                stderr_str = stderr_data if isinstance(stderr_data, str) else stderr_data.decode('utf-8', errors='replace')
        except subprocess.TimeoutExpired:
            logger.warning(f"Process timeout after {timeout}s, killing process...")
            if process:
                try:
                    process.kill()
                except:
                    pass
                # Try to get any remaining output after kill (with short timeout)
                try:
                    stdout_data, stderr_data = process.communicate(timeout=2)
                    if binary:
                        stdout_bytes = stdout_data if isinstance(stdout_data, bytes) else stdout_data.encode('utf-8', errors='replace')
                        stderr_str = stderr_data.decode('utf-8', errors='replace') if isinstance(stderr_data, bytes) else stderr_data
                    else:
                        stdout_str = stdout_data if isinstance(stdout_data, str) else stdout_data.decode('utf-8', errors='replace')
                        stderr_str = stderr_data if isinstance(stderr_data, str) else stderr_data.decode('utf-8', errors='replace')
                except:
                    if binary:
                        stdout_bytes, stderr_str = b'', ''
                    else:
                        stdout_str, stderr_str = '', ''
            else:
                if binary:
                    stdout_bytes, stderr_str = b'', ''
                else:
                    stdout_str, stderr_str = '', ''
            returncode = -1
            raise
        finally:
            # Ensure process is cleaned up
            if process:
                try:
                    # Close file descriptors to free resources
                    if process.stdout:
                        process.stdout.close()
                    if process.stderr:
                        process.stderr.close()
                    if process.stdin:
                        process.stdin.close()
                except:
                    pass
        
        logger.debug(f"Process finished with returncode={returncode}")
        
        # Strip ANSI codes from output
        if binary:
            # For binary mode, keep stdout as bytes, only clean stderr
            stdout_bytes = stdout_bytes  # Keep as bytes
            stderr_content = strip_ansi_codes(stderr_str) if stderr_str else ""
            logger.debug(f"Output reading completed: stdout_length={len(stdout_bytes)} bytes, stderr_length={len(stderr_content)}")
        else:
            # For text mode, clean both stdout and stderr
            stdout_content = strip_ansi_codes(stdout_str) if stdout_str else ""
            stderr_content = strip_ansi_codes(stderr_str) if stderr_str else ""
            logger.debug(f"Output reading completed: stdout_length={len(stdout_content)}, stderr_length={len(stderr_content)}")
            
            # Log output for debugging (text mode only)
            if stdout_content:
                for line in stdout_content.strip().split('\n'):
                    if line.strip():
                        logger.debug(f"rclone stdout: {line}")
        
        if stderr_content:
            for line in stderr_content.strip().split('\n'):
                if line.strip():
                    logger.debug(f"rclone stderr: {line}")
        
        # Log command completion
        logger.info(f"Command completed: {' '.join(cmd)} (exit_code={returncode}, success={returncode == 0})")
        
        if binary:
            return {
                "success": returncode == 0,
                "exit_code": returncode,
                "stdout": stdout_bytes,  # Return as bytes
                "stderr": stderr_content if stderr_content else None,
            }
        else:
            return {
                "success": returncode == 0,
                "exit_code": returncode,
                "stdout": stdout_content,
                "stderr": stderr_content if stderr_content else None,
                "stdout_lines": stdout_content.strip().split('\n') if stdout_content else []
            }
        
    except subprocess.TimeoutExpired:
        error_msg = f"rclone {description} timed out after {timeout} seconds"
        logger.error(error_msg)
        return {"error": error_msg, "success": False, "exit_code": -1}
    except FileNotFoundError:
        error_msg = f"rclone executable not found: {rclone_exe}. Please install rclone or set RCLONE_EXE_PATH."
        logger.error(error_msg)
        return {"error": error_msg, "success": False}
    except Exception as e:
        error_msg = f"rclone {description} failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg, "success": False}

