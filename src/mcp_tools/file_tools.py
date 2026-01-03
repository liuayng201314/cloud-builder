"""MCP tools for file operations."""

import os
import json
import re
from typing import Optional, Dict, Any

from log_config.logging_config import get_logger
from utils.ansi_utils import strip_ansi_codes, clean_dict_for_json
from utils.error_utils import return_error
from rclone.rclone_executor import execute_rclone_command
from rclone.rclone_operations import ensure_remote_directory_exists

logger = get_logger("CloudBuilder.FileTools")


def upload_file(
    local_file_path: str,
    remote_file_path: Optional[str],
    remote_host_name: str,
    local_path: str,
    remote_path: str,
    rclone_exe_path: str = None
) -> Dict[str, Any]:
    """
    Upload a single file to the remote server using rclone.
    
    Args:
        local_file_path: Path to the local file to upload (absolute path recommended)
        remote_file_path: Remote destination path (optional, will use same relative path)
        remote_host_name: Remote host name
        local_path: Default local path (used to resolve relative paths)
        remote_path: Default remote path
        rclone_exe_path: Path to rclone executable (optional)
    
    Returns:
        Dictionary with upload result
    """
    logger.info(f"Starting file upload using rclone: {local_file_path}")
    
    # Resolve relative paths if needed (compatibility fallback)
    resolved_local_file_path = local_file_path
    if not os.path.isabs(local_file_path):
        # Try to resolve relative to local_path if it exists
        if local_path and os.path.exists(local_path):
            candidate_path = os.path.join(local_path, local_file_path)
            if os.path.exists(candidate_path):
                resolved_local_file_path = os.path.abspath(candidate_path)
                logger.info(f"Resolved relative path '{local_file_path}' to '{resolved_local_file_path}' based on LOCAL_PATH")
            else:
                # Try current working directory
                candidate_path = os.path.abspath(local_file_path)
                if os.path.exists(candidate_path):
                    resolved_local_file_path = candidate_path
                    logger.info(f"Resolved relative path '{local_file_path}' to '{resolved_local_file_path}' based on current working directory")
                else:
                    error_msg = (
                        f"Local file does not exist: {local_file_path}. "
                        f"Please use absolute path. Tried: {os.path.join(local_path, local_file_path)} and {candidate_path}"
                    )
                    logger.error(error_msg)
                    return return_error(error_msg)
        else:
            # Try current working directory
            candidate_path = os.path.abspath(local_file_path)
            if os.path.exists(candidate_path):
                resolved_local_file_path = candidate_path
                logger.info(f"Resolved relative path '{local_file_path}' to '{resolved_local_file_path}' based on current working directory")
            else:
                error_msg = (
                    f"Local file does not exist: {local_file_path}. "
                    f"Please use absolute path. Tried: {candidate_path}"
                )
                logger.error(error_msg)
                return return_error(error_msg)
    else:
        # Already absolute path, normalize it
        resolved_local_file_path = os.path.abspath(local_file_path)
    
    if not os.path.exists(resolved_local_file_path):
        error_msg = f"Local file does not exist: {resolved_local_file_path}"
        logger.error(error_msg)
        return return_error(error_msg)
    
    if not os.path.isfile(resolved_local_file_path):
        error_msg = f"Path is not a file: {resolved_local_file_path}"
        logger.error(error_msg)
        return return_error(error_msg)
    
    # Use resolved path for the rest of the function
    local_file_path = resolved_local_file_path
    
    if not remote_host_name:
        error_msg = "REMOTE_HOST_NAME environment variable must be set to use rclone"
        logger.error(error_msg)
        return return_error(error_msg)
    
    # Determine remote path
    if remote_file_path is None:
        if local_path and remote_path:
            # Normalize both paths for comparison
            local_path_abs = os.path.abspath(local_path)
            if local_file_path.startswith(local_path_abs):
                relative_path = os.path.relpath(local_file_path, local_path_abs)
                remote_file_path = os.path.join(remote_path, relative_path).replace('\\', '/')
                logger.debug(f"Determined remote path: {remote_file_path}")
            else:
                # If file is not under local_path, use just the filename
                filename = os.path.basename(local_file_path)
                remote_file_path = os.path.join(remote_path, filename).replace('\\', '/')
                logger.debug(f"File not under LOCAL_PATH, using filename only. Remote path: {remote_file_path}")
        else:
            error_msg = "Remote path not specified and no default paths configured."
            logger.error(error_msg)
            return return_error(error_msg)
    
    # Determine rclone executable path
    rclone_exe = rclone_exe_path or "rclone"
    if rclone_exe_path and not os.path.exists(rclone_exe_path):
        error_msg = f"RCLONE_EXE_PATH specified but file does not exist: {rclone_exe_path}"
        logger.error(error_msg)
        return return_error(error_msg)
    
    local_size = os.path.getsize(local_file_path)
    logger.info(f"Uploading file: {local_file_path} -> {remote_host_name}:{remote_file_path} ({local_size} bytes)")
    
    # Ensure remote directory exists before uploading
    remote_dir = os.path.dirname(remote_file_path)
    if remote_dir:  # Only check if there's a directory path (not root)
        if not ensure_remote_directory_exists(remote_dir, remote_host_name, rclone_exe_path):
            error_msg = f"Failed to ensure remote directory exists: {remote_dir}"
            logger.error(error_msg)
            return return_error(error_msg)
    
    # Calculate timeout based on file size
    # Assume minimum transfer speed of 100 KB/s, add 30 seconds buffer
    # For very large files, cap at 1 hour
    min_speed_bytes_per_sec = 100 * 1024  # 100 KB/s
    estimated_timeout = max(60, (local_size / min_speed_bytes_per_sec) + 30)  # At least 1 minute
    timeout_seconds = min(estimated_timeout, 3600)  # Cap at 1 hour
    
    logger.debug(f"Calculated timeout for file upload: {timeout_seconds:.1f} seconds (file size: {local_size} bytes)")
    
    try:
        # Build rclone copyto command
        cmd = [rclone_exe, "copyto"]
        cmd.append("--verbose")
        cmd.append(os.path.abspath(local_file_path))
        
        # Destination: remote_name:remote_path
        remote_dest = f"{remote_host_name}:{remote_file_path}"
        cmd.append(remote_dest)
        
        # Execute rclone copyto using execute_rclone_command for consistency
        result = execute_rclone_command(
            cmd,
            "copyto",
            remote_host_name,
            rclone_exe_path,
            timeout=int(timeout_seconds)
        )
        
        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            exit_code = result.get("exit_code", -1)
            stderr_content = result.get("stderr", "") or ""
            
            # Clean error message to remove any ANSI codes
            if stderr_content:
                cleaned_stderr = strip_ansi_codes(stderr_content)
                error_msg = f"rclone copyto failed: {cleaned_stderr}"
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
        
        logger.info(f"File uploaded successfully: {remote_dest} (local: {local_size} bytes)")
        
        result_dict = {
            "success": True,
            "local_file": local_file_path,
            "remote_file": remote_file_path,
            "remote_dest": remote_dest,
            "file_size": local_size,
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
        error_msg = f"Upload failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return return_error(error_msg)


def read_remote_file(
    remote_file_path: str,
    encoding: str,
    remote_host_name: str,
    rclone_exe_path: str = None
) -> Dict[str, Any]:
    """
    Read the contents of a file from the remote server using rclone.
    
    Args:
        remote_file_path: Path to the remote file to read
        encoding: Text encoding to use (default: utf-8)
        remote_host_name: Remote host name
        rclone_exe_path: Path to rclone executable (optional)
    
    Returns:
        Dictionary with file contents or error
    """
    logger.info(f"Reading remote file using rclone: {remote_file_path} (encoding: {encoding})")
    
    if not remote_host_name:
        error_msg = "REMOTE_HOST_NAME environment variable must be set to use rclone"
        logger.error(error_msg)
        return return_error(error_msg)
    
    rclone_exe = rclone_exe_path or "rclone"
    if rclone_exe_path and not os.path.exists(rclone_exe_path):
        error_msg = f"RCLONE_EXE_PATH specified but file does not exist: {rclone_exe_path}"
        logger.error(error_msg)
        return return_error(error_msg)
    
    remote_dest = f"{remote_host_name}:{remote_file_path}"
    
    # Build rclone cat command
    cmd = [rclone_exe, "cat", remote_dest]
    
    try:
        # Use binary mode to get raw bytes, then decode with specified encoding
        result = execute_rclone_command(
            cmd,
            "cat",
            remote_host_name,
            rclone_exe_path,
            timeout=300,
            binary=True
        )
        
        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            exit_code = result.get("exit_code", -1)
            stderr_content = result.get("stderr", "") or ""
            
            # Check for specific error conditions
            if stderr_content:
                if "file not found" in stderr_content.lower() or "doesn't exist" in stderr_content.lower():
                    error_msg = f"File not found on remote server: {remote_file_path}"
                else:
                    error_msg = f"rclone cat failed: {stderr_content}"
            error_msg = strip_ansi_codes(error_msg)  # Ensure error message is clean
            logger.error(error_msg)
            return return_error(error_msg)
        
        # Get binary output from result
        stdout_bytes = result.get("stdout", b"")
        if not isinstance(stdout_bytes, bytes):
            # Fallback: convert to bytes if somehow it's not bytes
            stdout_bytes = stdout_bytes.encode('utf-8', errors='replace') if stdout_bytes else b""
        
        # Decode with specified encoding
        try:
            content = stdout_bytes.decode(encoding)
        except UnicodeDecodeError as e:
            error_msg = f"Failed to decode file with {encoding} encoding: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return return_error(error_msg)
        
        file_size = len(stdout_bytes)
        logger.info(f"Successfully read remote file: {remote_file_path} ({file_size} bytes, {len(content)} characters)")
        
        result_dict = {
            "success": True,
            "file_path": remote_file_path,
            "content": content,
            "file_size": file_size,
            "encoding": encoding
        }
        # Clean all string values to ensure JSON safety
        return clean_dict_for_json(result_dict)
        
    except FileNotFoundError:
        error_msg = f"rclone executable not found: {rclone_exe}. Please install rclone or set RCLONE_EXE_PATH."
        logger.error(error_msg)
        return return_error(error_msg)
    except Exception as e:
        error_msg = f"Failed to read remote file: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return return_error(error_msg)


def list_remote_directory(
    remote_dir_path: str,
    remote_host_name: str,
    rclone_exe_path: str = None
) -> Dict[str, Any]:
    """
    List contents of a remote directory using rclone.
    
    Args:
        remote_dir_path: Path to the remote directory to list
        remote_host_name: Remote host name
        rclone_exe_path: Path to rclone executable (optional)
    
    Returns:
        Dictionary with directory contents
    """
    logger.info(f"Listing remote directory using rclone: {remote_dir_path}")
    
    if not remote_host_name:
        error_msg = "REMOTE_HOST_NAME environment variable must be set to use rclone"
        logger.error(error_msg)
        return return_error(error_msg)
    
    rclone_exe = rclone_exe_path or "rclone"
    if rclone_exe_path and not os.path.exists(rclone_exe_path):
        error_msg = f"RCLONE_EXE_PATH specified but file does not exist: {rclone_exe_path}"
        logger.error(error_msg)
        return return_error(error_msg)
    
    remote_dest = f"{remote_host_name}:{remote_dir_path}"
    
    # Build rclone lsjson command
    cmd = [rclone_exe, "lsjson", remote_dest]
    
    # Use 60 seconds timeout for directory listing
    result = execute_rclone_command(
        cmd,
        "lsjson",
        remote_host_name,
        rclone_exe_path,
        timeout=60
    )
    
    if not result.get("success"):
        error_msg = result.get("error", "Unknown error")
        exit_code = result.get("exit_code", -1)
        stderr = result.get("stderr", "")
        
        # Check for specific error conditions
        if exit_code != 0:
            stderr_lower = stderr.lower() if stderr else ""
            if any(keyword in stderr_lower for keyword in ["file not found", "doesn't exist", "no such file", "directory not found"]):
                error_msg = f"Directory not found: {remote_dir_path}"
            elif "timed out" in error_msg.lower():
                error_msg = f"Directory listing timed out. The directory '{remote_dir_path}' may not exist or be inaccessible."
            elif stderr:
                cleaned_stderr = strip_ansi_codes(stderr.strip())
                error_msg = f"Failed to list directory: {cleaned_stderr}"
        
        # Clean error message to ensure JSON safety
        error_msg = strip_ansi_codes(error_msg)
        logger.error(error_msg)
        return clean_dict_for_json({"error": error_msg})
    
    # Parse JSON output from rclone lsjson
    try:
        json_output = result.get("stdout", "")
        # CRITICAL: Clean JSON output before parsing to remove any ANSI codes
        json_output = strip_ansi_codes(json_output) if json_output else ""
        if not json_output.strip():
            # Empty directory - rclone lsjson returns empty array [] for empty directories
            items = []
        else:
            # Try to parse JSON - if it fails, it might still contain ANSI codes
            try:
                items_data = json.loads(json_output)
            except json.JSONDecodeError as parse_error:
                # If parsing fails, try to extract JSON from potentially mixed output
                # Look for JSON array or object pattern
                json_match = re.search(r'(\[.*\]|\{.*\})', json_output, re.DOTALL)
                if json_match:
                    json_output = json_match.group(1)
                    json_output = strip_ansi_codes(json_output)  # Clean again
                    items_data = json.loads(json_output)
                else:
                    raise parse_error
            # rclone lsjson returns a list of file/directory objects
            items = []
            for item in items_data:
                items.append({
                    "name": item.get("Path", item.get("Name", "")),
                    "size": item.get("Size", 0),
                    "is_directory": item.get("IsDir", False),
                    "modified_time": item.get("ModTime", {}).get("Unix", 0) if isinstance(item.get("ModTime"), dict) else 0,
                    "permissions": None  # rclone lsjson doesn't provide permissions
                })
    except json.JSONDecodeError as e:
        stdout_preview = result.get('stdout', '')[:200]
        stdout_preview = strip_ansi_codes(stdout_preview)  # Clean preview
        error_msg = f"Failed to parse rclone lsjson output: {str(e)}. Output: {stdout_preview}"
        error_msg = strip_ansi_codes(error_msg)  # Ensure clean
        logger.error(error_msg, exc_info=True)
        return clean_dict_for_json({"error": error_msg})
    except Exception as e:
        error_msg = f"Failed to process directory listing: {str(e)}"
        error_msg = strip_ansi_codes(error_msg)  # Ensure clean
        logger.error(error_msg, exc_info=True)
        return clean_dict_for_json({"error": error_msg})
    
    logger.info(f"Successfully listed directory: {remote_dir_path} ({len(items)} items)")
    
    result_dict = {
        "success": True,
        "directory": remote_dir_path,
        "items": items,
        "total_items": len(items)
    }
    # Clean all string values to ensure JSON safety
    return clean_dict_for_json(result_dict)

