# CloudBuilder MCP Service

A Model Context Protocol (MCP) server that provides comprehensive cloud build workflow support. Through rclone, it enables file synchronization, remote command execution, and automated builds, helping developers achieve a cloud development model of local development and remote building.

## ✨ Core Features

- 📁 **Directory Synchronization**: Intelligently sync local directories to remote servers with support for ignore rules and incremental updates
- 📤 **File Upload**: Quickly upload individual files to remote servers
- 📖 **File Reading**: Read file contents from remote servers with support for multiple encoding formats
- 🖥️ **Remote Command Execution**: Execute commands on remote servers via SSH
- 📋 **Directory Browsing**: List remote directory contents and view detailed file information
- 🔧 **Automated Builds**: Support for automatic builds after synchronization with automatic compilation error fixing
- ⚙️ **Flexible Configuration**: Support for project-level configuration and environment variable configuration

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- rclone (for file transfer operations, supports multiple backends such as SFTP, S3, FTP, etc.)
- MCP client (such as Claude Desktop, Cursor, etc.)

### Installing Dependencies

#### Method 1: Using pip (Recommended)

```bash
pip install -r requirements.txt
```

#### Method 2: Using uv

```bash
uv sync
```

### Configuring rclone

1. **Install rclone**: Download and install from [rclone official website](https://rclone.org/)
2. **Configuration**

- **GUI Method:**

  GUI Download: https://github.com/rclone/rclone-webui-react

  Load command: `rclone rcd --rc-web-gui --rc-user=abc --rc-pass=abcd ./ui`

  Then configure via the GUI.

- **Command Line Method:**

  **Configure Remote Storage**: Run `rclone config` to create remote configuration. rclone supports multiple backend types (SFTP, S3, FTP, Google Drive, etc.)

  ```bash
  rclone config
  ```

  **SFTP Configuration Example**:

  ```ini
  [route84]
  type = sftp
  host = 192.0.0.1
  user = xxxx
  pass = <obscured_password>  # Password encrypted using rclone obscure
  shell_type = unix
  port = 22  # Optional, defaults to 22
  ```

  **Note**: rclone supports multiple storage backends. You can configure different types of remote storage such as SFTP, S3, FTP, etc., according to your needs.

3. **Configuration File Location**: rclone automatically searches for configuration files in the following order:
   - Path specified by `RCLONE_CONFIG` environment variable
   - `rclone.conf` in the current working directory
   - `rclone.conf` in the Python script directory
   - Windows: `%APPDATA%\rclone\rclone.conf`
   - Linux/Mac: `~/.config/rclone/rclone.conf` or `~/.rclone.conf`

### Configuring MCP Client

Add server configuration to the MCP client configuration file (using Claude Desktop as an example, the configuration file is usually located at `~/Library/Application Support/Claude/claude_desktop_config.json` or the corresponding location on Windows):

```json
{
  "mcpServers": {
    "cloud-builder": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/cloud-builder",
        "run",
        "python",
        "src/main.py"
      ],
      "env": {
        "RCLONE_EXE_PATH": "D:\\dev\\rclone\\rclone.exe",
        "PROJECT_PATH": "${workspaceFolder}"
      }
    }
  }
}
```

**Important Notes**:

- Replace `/path/to/cloud-builder` with the **absolute path** to the project root directory
- The `PROJECT_PATH` environment variable is used to specify the current working project directory. The server will look for the `.cloudbuilder.json` configuration file in this directory
- The server uses stdio transport and does not require a network port

## ⚙️ Configuration Methods

CloudBuilder supports two configuration methods, with **project-level configuration taking precedence over environment variables**.

### 1. Project-Level Configuration (Recommended)

Create a `.cloudbuilder.json` file in each project root directory:

```json
{
  "REMOTE_HOST_NAME": "route84",
  "LOCAL_PATH": "E:\\AI\\test_c",
  "REMOTE_PATH": "/home/xxxx/ftp_dir",
  "BUILD_COMMAND": "/home/xxxx/ftp_dir/build.sh"
}
```

**Advantages**:

- ✅ Each project can have independent configuration
- ✅ Configuration is managed together with project code (can be committed to version control)
- ✅ Automatically uses corresponding configuration when switching projects

**Search Logic**: The server searches for the `.cloudbuilder.json` file in the directory specified by the `PROJECT_PATH` environment variable.

### 2. Environment Variable Configuration

Set environment variables in the MCP client configuration:

```json
{
  "mcpServers": {
    "cloud-builder": {
      "command": "python",
      "args": ["-m", "src.main"],
      "env": {
        "REMOTE_HOST_NAME": "route84",
        "RCLONE_EXE_PATH": "D:\\dev\\rclone\\rclone.exe",
        "LOCAL_PATH": "E:\\AI\\test_c",
        "REMOTE_PATH": "/home/xxxx/ftp_dir",
        "BUILD_COMMAND": "/home/xxxx/ftp_dir/build.sh"
      }
    }
  }
}
```

### Configuration Items

| Configuration Item | Description                                              | Required | Notes                                                                |
| ------------------ | -------------------------------------------------------- | -------- | -------------------------------------------------------------------- |
| `REMOTE_HOST_NAME` | Remote configuration name in rclone.conf (e.g., route84) | ✅       | Must exactly match the name in rclone configuration (case-sensitive) |
| `RCLONE_EXE_PATH`  | Path to rclone executable file                           | ✅       | Optional, recommended to set for path validation                     |
| `LOCAL_PATH`       | Local project directory path                             | ✅       | Local root directory for file synchronization                        |
| `REMOTE_PATH`      | Remote server directory path                             | ✅       | Remote root directory for file synchronization                       |
| `BUILD_COMMAND`    | Build command                                            | ✅       | Optional, used for automated build workflows                         |

**Important Notes**:

- Remote connection information (host, user, pass, port, etc.) is automatically read from rclone.conf and does not need to be set in the configuration
- Passwords are encrypted/decrypted using rclone's obscure algorithm, no manual handling required
- rclone supports multiple backend types (SFTP, S3, FTP, etc.), and configuration methods may vary slightly
- Synchronization ignore rules are read from the project's `.sync_rules` file (rclone filter format)

### Synchronization Ignore Rules

Create a `.sync_rules` file in the project root directory using rclone filter format:

```
- .specstory/**
- .cursorindexingignore
- build/**
- *.log
- node_modules/**
```

## 🛠️ MCP Tools

### sync_directory

Synchronize local directory to remote server (via rclone).

**Parameters**:

- `local_dir` (optional): Local directory path, defaults to `LOCAL_PATH` configuration
- `remote_dir` (optional): Remote directory path, defaults to `REMOTE_PATH` configuration
- `delete_excess` (optional): Whether to delete files in the target that don't exist in the source, defaults to `true`

**Returns**: Dictionary containing synchronization results, including:

- List and statistics of uploaded files
- List of created directories
- List of deleted files (if enabled)
- List of ignored items
- Error messages (if any)

**Examples**:

```python
# Use default configuration paths
sync_directory()

# Specify custom paths
sync_directory("/custom/local/path", "/custom/remote/path")

# Disable deleting excess files
sync_directory(delete_excess=False)
```

### upload_file

Upload a single file to remote server (via rclone).

**Parameters**:

- `local_file_path`: Local file path to upload (recommended to use absolute path, or relative path relative to `LOCAL_PATH`)
- `remote_file_path` (optional): Remote target path. If not specified, automatically determined based on `LOCAL_PATH`/`REMOTE_PATH` mapping

**Returns**: Dictionary containing upload results, including file size and path information.

**Examples**:

```python
# Automatically determine remote path (based on LOCAL_PATH/REMOTE_PATH mapping)
upload_file("E:\\AI\\test_c\\main.c")

# Specify exact remote target path
upload_file("E:\\AI\\test_c\\main.c", "/home/xxxx/ftp_dir/main.c")
```

### read_remote_file

Read file content from remote server (via rclone).

**Parameters**:

- `remote_file_path`: Remote file path to read
- `encoding` (optional): Text encoding format, defaults to `utf-8`

**Returns**: Dictionary containing file content, size, and encoding information.

**Examples**:

```python
# Read using default UTF-8 encoding
read_remote_file("/home/xxxx/ftp_dir/main.c")

# Specify encoding format
read_remote_file("/home/xxxx/ftp_dir/main.c", "latin-1")
```

### execute_remote_command

Execute commands on remote server via SSH.

**Parameters**:

- `command`: Command to execute on remote server
- `working_directory` (optional): Working directory for the command

**Returns**: Dictionary containing command output, exit code, stdout, and stderr.

**Examples**:

```python
# Simple command
execute_remote_command("ls -la")

# Command with working directory
execute_remote_command("make clean", "/home/xxxx/ftp_dir")

# Execute build command
execute_remote_command("/home/xxxx/ftp_dir/build.sh")
```

### list_remote_directory

List contents of remote directory (via rclone).

**Parameters**:

- `remote_dir_path`: Remote directory path to list

**Returns**: Dictionary containing directory contents, including file names, sizes, permissions, and type information.

**Examples**:

```python
list_remote_directory("/home/xxxx/ftp_dir")
```

## 📚 MCP Resources

### cloudbuilder://config

Get current CloudBuilder server configuration information (does not include sensitive data such as passwords).

**Returns**: JSON containing the following information:

- Connection status (configured/incomplete)
- Remote server information (host, port, username)
- Path configuration (local path, remote path)
- Build command (if configured)
- Missing or incomplete settings

## 💡 MCP Prompts (Workflows)

### check_config_workflow

Workflow prompt for checking CloudBuilder configuration. Guides how to:

1. Get current configuration
2. Check configuration completeness
3. Report missing configuration items

### sync_workflow

File synchronization workflow prompt. Provides step-by-step guidance for synchronizing files to remote servers.

### build_workflow

Remote build workflow prompt. Supports:

1. Executing build commands on remote servers
2. Automatically reading compilation errors
3. Automatically fixing errors (up to 5 attempts)
4. Converting remote file paths to local paths for fixing

### sync_and_build_workflow

Complete workflow prompt for synchronization and building. Combines file synchronization and automated building, including:

1. Synchronizing files to remote servers
2. Executing build commands
3. Automatically fixing compilation errors
4. Repeating until build succeeds or maximum attempts reached

## 🔒 Security Considerations

- ✅ **Stdio Transport**: Server uses stdio transport, eliminating network security issues
- ✅ **Password Encryption**: Remote credentials stored in rclone.conf using rclone's obscure algorithm encryption
- ✅ **Automatic Decryption**: Passwords automatically decrypted, no need to store in plain text in environment variables
- ✅ **Sensitive Data Protection**: Sensitive data (such as passwords) will not be exposed in logs or responses
- ✅ **Path Restrictions**: All file operations are restricted to configured paths
- ✅ **SSH Security**: SSH connections use paramiko with appropriate host key handling
- ✅ **Multi-Backend Support**: Support for multiple storage backends (SFTP, S3, FTP, etc.) through rclone

## 🐛 Troubleshooting

### Connection Issues

**Problem**: Unable to connect to remote server

**Solutions**:

1. Verify that `REMOTE_HOST_NAME` exactly matches the remote configuration name in rclone.conf (case-sensitive)
2. Check if rclone.conf configuration file exists and is readable
3. Verify that configuration fields in rclone.conf are correct (fields may vary depending on backend type)
   - SFTP: `host`, `user`, `pass`, `port`, etc.
   - S3: `access_key_id`, `secret_access_key`, `region`, etc.
   - For other backends, refer to rclone documentation
4. If there is a `port` field in the configuration (such as SFTP), ensure the port number is correct (default is 22)
5. Check if the remote server is accessible from your network
6. Use `rclone config show <remote_name>` to verify the configuration is correct
7. Test rclone connection: `rclone lsd <remote_name>:`

### Path Issues

**Problem**: File synchronization fails or path errors

**Solutions**:

1. Verify that `LOCAL_PATH` exists and is readable
2. Ensure that `REMOTE_PATH` exists on the remote server and has write permissions
3. Check file permissions on local and remote systems
4. Use absolute paths instead of relative paths
5. Verify path mapping is correct (`LOCAL_PATH` → `REMOTE_PATH`)

### Configuration Issues

**Problem**: Configuration not taking effect or configuration file not found

**Solutions**:

1. Check if `PROJECT_PATH` environment variable is set correctly
2. Confirm that `.cloudbuilder.json` file is located in the project root directory
3. Verify JSON format is correct (can use JSON validation tools)
4. Check if configuration item names are spelled correctly
5. View server logs to understand the configuration loading process

### rclone Configuration Issues

**Problem**: rclone operations fail

**Solutions**:

1. Ensure rclone.conf file is in a searchable location (see configuration file location instructions above)
2. Use `rclone config paths` to view rclone's configuration file path
3. Verify remote configuration name is spelled correctly (case-sensitive)
4. If password decryption fails, check if the pass field (if applicable) is a valid obscure encrypted value
5. You can use `python src/rclone/rclone_decrypt_pass.py --remote <remote_name>` to test configuration reading
6. If `RCLONE_EXE_PATH` is set, verify the path exists and is executable
7. Depending on the backend type used, ensure all required configuration fields are correctly set

### Synchronization Ignore Rules Issues

**Problem**: Files that shouldn't be synchronized are being synchronized, or files that should be synchronized are being ignored

**Solutions**:

1. Check if `.sync_rules` file format is correct (rclone filter format)
2. Patterns support Unix-style wildcards (`*`, `?`, `[]`)
3. Directory patterns should end with `/`
4. Use `-` prefix to indicate exclusion patterns
5. Test rules: `rclone ls <remote_name>:<remote_path> --filter-from .sync_rules`

### Build Command Issues

**Problem**: Build command execution fails

**Solutions**:

1. Verify that `BUILD_COMMAND` path is correct
2. Ensure build command is executable on remote server
3. Check working directory permissions on remote server
4. View error messages in command output
5. Try manually executing the build command on remote server to verify

## 📝 Usage Examples

### Complete Workflow Example

1. **Check Configuration**:

   ```
   Use check_config_workflow prompt to check current configuration
   ```

2. **Synchronize Files**:

   ```
   Use sync_workflow prompt to synchronize local files to remote server
   ```

3. **Execute Build**:

   ```
   Use build_workflow prompt to build project on remote server
   ```

4. **Synchronize and Build**:

   ```
   Use sync_and_build_workflow prompt to complete the full synchronization and build process
   ```

### Manual Tool Call Examples

```python
# 1. Synchronize entire project directory
sync_directory()

# 2. Upload a single file
upload_file("src/main.c")

# 3. Read remote file
read_remote_file("/home/xxxx/ftp_dir/src/main.c")

# 4. Execute build command
execute_remote_command("/home/xxxx/ftp_dir/build.sh", "/home/xxxx/ftp_dir")

# 5. List remote directory
list_remote_directory("/home/xxxx/ftp_dir")
```

---

**Note**: MCP servers typically don't need to be run manually. They are automatically started and managed by MCP clients (such as Claude Desktop, Cursor). If you need to test manually, you can use:

```bash
uv run python src/main.py
```
