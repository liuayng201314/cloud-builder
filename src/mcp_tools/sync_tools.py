"""MCP tools for directory synchronization."""

import os
from typing import Optional, Dict, Any

from log_config.logging_config import get_logger
from utils.ansi_utils import strip_ansi_codes, clean_dict_for_json
from utils.error_utils import return_error
from rclone.rclone_executor import execute_rclone_command
from rclone.rclone_operations import ensure_remote_directory_exists

logger = get_logger("CloudBuilder.SyncTools")


def sync_directory(
    local_dir: Optional[str],
    remote_dir: Optional[str],
    delete_excess: bool,
    remote_host_name: str,
    local_path: str,
    remote_path: str,
    rclone_exe_path: str = None
) -> Dict[str, Any]:
    """
    Synchronize a local directory to remote server using rclone.
    
    Args:
        local_dir: Local directory path (defaults to local_path)
        remote_dir: Remote directory path (defaults to remote_path)
        delete_excess: Delete files in destination that don't exist in source (default: True)
        remote_host_name: Remote host name
        local_path: Default local path
        remote_path: Default remote path
        rclone_exe_path: Path to rclone executable (optional)
    
    Returns:
        Dictionary with sync results including statistics and any errors
    """
    logger.info("Starting directory synchronization using rclone")
    
    # Normalize parameters: handle empty strings as None
    if local_dir == "":
        local_dir = None
    if remote_dir == "":
        remote_dir = None
    
    # Use parameters or defaults
    local_path_used = local_dir or local_path
    remote_path_used = remote_dir or remote_path
    
    if not local_path_used or not remote_path_used:
        error_msg = "Local and remote paths must be specified either as parameters or environment variables"
        logger.error(error_msg)
        return return_error(error_msg)
    
    if not remote_host_name:
        error_msg = "REMOTE_HOST_NAME environment variable must be set to use rclone sync"
        logger.error(error_msg)
        return return_error(error_msg)
    
    if not os.path.exists(local_path_used):
        error_msg = f"Local path does not exist: {local_path_used}"
        logger.error(error_msg)
        return return_error(error_msg)
    
    # Determine rclone executable path
    rclone_exe = rclone_exe_path or "rclone"
    if rclone_exe_path and not os.path.exists(rclone_exe_path):
        error_msg = f"RCLONE_EXE_PATH specified but file does not exist: {rclone_exe_path}"
        logger.error(error_msg)
        return return_error(error_msg)
    
    logger.info(f"Syncing from '{local_path_used}' to '{remote_host_name}:{remote_path_used}' using rclone (delete_excess={delete_excess})")
    
    # Ensure remote directory exists before syncing
    if not ensure_remote_directory_exists(remote_path_used, remote_host_name, rclone_exe_path):
        error_msg = f"Failed to ensure remote directory exists: {remote_path_used}"
        logger.error(error_msg)
        return return_error(error_msg)
    
    try:
        # Build rclone sync command
        # rclone sync source:path dest:path [flags]
        # Use 'sync' command which deletes files in destination that don't exist in source
        cmd = [rclone_exe, "sync"]
        
        # Add filter rules from .sync_rules file
        # .sync_rules file should be in rclone filter format directly
        # rclone filter format: - pattern (exclude) or + pattern (include)
        rules_file = os.path.join(local_path_used, '.sync_rules')
        if os.path.exists(rules_file):
            logger.debug(f"Found .sync_rules file: {rules_file}")
            # Use --filter-from to read rclone filter rules directly
            cmd.extend(["--filter-from", rules_file])
            logger.debug(f"Using --filter-from {rules_file} (rclone filter format)")
        
        # Add verbose output for better logging
        cmd.append("--verbose")
        
        # Add stats output for better statistics
        cmd.append("--stats=1s")
        
        # Source: local directory
        cmd.append(os.path.abspath(local_path_used))
        
        # Destination: remote_name:remote_path
        remote_dest = f"{remote_host_name}:{remote_path_used}"
        cmd.append(remote_dest)
        
        # Execute rclone sync using execute_rclone_command for consistency
        # Use 60 minutes timeout for large directory syncs
        result = execute_rclone_command(
            cmd,
            "sync",
            remote_host_name,
            rclone_exe_path,
            timeout=3600
        )
        
        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            exit_code = result.get("exit_code", -1)
            stderr_content = result.get("stderr", "") or ""
            
            # Clean error message to remove any ANSI codes
            if stderr_content:
                cleaned_stderr = strip_ansi_codes(stderr_content)
                error_msg = f"rclone sync failed: {cleaned_stderr}"
            error_msg = strip_ansi_codes(error_msg)  # Ensure error message is clean
            logger.error(error_msg)
            result_dict = {
                "error": error_msg,
                "exit_code": exit_code,
                "stdout": result.get("stdout", ""),
                "stderr": stderr_content
            }
            # Clean all string values to ensure JSON safety
            return clean_dict_for_json(result_dict)
        
        # Get results from execute_rclone_command
        stdout_content = result.get("stdout", "") or ""
        stderr_content = result.get("stderr", "") or ""
        exit_code = result.get("exit_code", 0)
        stdout_lines = result.get("stdout_lines", [])
        
        # Parse rclone output to extract statistics
        stats = {
            "transferred": 0,
            "errors": 0,
            "checks": 0,
            "elapsed_time": None
        }
        
        for line in stdout_lines:
            if "Transferred:" in line and "/" in line:
                # Try to extract number of files transferred
                try:
                    parts = line.split("Transferred:")[1].strip().split(",")
                    if len(parts) > 0:
                        # Get the number part (e.g., "5" from "5 / 5")
                        num_part = parts[0].strip().split()[0]
                        stats["transferred"] = int(num_part)
                except:
                    pass
            elif "Errors:" in line:
                try:
                    stats["errors"] = int(line.split("Errors:")[1].strip().split()[0])
                except:
                    pass
            elif "Checks:" in line:
                try:
                    stats["checks"] = int(line.split("Checks:")[1].strip().split()[0])
                except:
                    pass
            elif "Elapsed time:" in line:
                try:
                    time_str = line.split("Elapsed time:")[1].strip()
                    stats["elapsed_time"] = time_str
                except:
                    pass
        
        logger.info(f"Sync completed: {stats['transferred']} files transferred, "
                   f"{stats['errors']} errors, elapsed time: {stats['elapsed_time']}")
        
        result_dict = {
            "success": True,
            "local_path": local_path_used,
            "remote_path": remote_path_used,
            "remote_dest": remote_dest,
            "stats": stats,
            "exit_code": exit_code,
            "stdout": stdout_content,
            "stderr": stderr_content if stderr_content else None
        }
        # Clean all string values to ensure JSON safety
        return clean_dict_for_json(result_dict)
        
    except FileNotFoundError:
        error_msg = f"rclone executable not found: {rclone_exe}. Please install rclone or set RCLONE_EXE_PATH."
        logger.error(error_msg)
        return return_error(error_msg)
    except Exception as e:
        error_msg = f"Sync failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return return_error(error_msg)

