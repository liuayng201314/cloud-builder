# CloudBuilder MCP 服务

一个基于模型上下文协议（MCP）的服务器，提供完整的云端构建工作流支持。通过 rclone 实现文件同步、远程命令执行和自动化构建，帮助开发者实现本地开发、远程构建的云端开发模式。

## ✨ 核心功能

- 📁 **目录同步**：智能同步本地目录到远程服务器，支持忽略规则和增量更新
- 📤 **文件上传**：快速上传单个文件到远程服务器
- 📖 **文件读取**：从远程服务器读取文件内容，支持多种编码格式
- 🖥️ **远程命令执行**：通过 SSH 在远程服务器上执行命令
- 📋 **目录浏览**：列出远程目录内容，查看文件详细信息
- 🔧 **自动化构建**：支持同步后自动构建，并可自动修复编译错误
- ⚙️ **灵活配置**：支持项目级配置和环境变量配置

## 🚀 快速开始

### 前置要求

- Python 3.12 或更高版本
- rclone（用于文件传输操作，支持多种后端如 SFTP、S3、FTP 等）
- MCP 客户端（如 Claude Desktop、Cursor 等）

### 安装依赖

#### 方法一：使用 pip（推荐）

```bash
pip install -r requirements.txt
```

#### 方法二：使用 uv

```bash
uv sync
```

### 配置 rclone

1. **安装 rclone**：从 [rclone 官网](https://rclone.org/) 下载并安装
2. **配置**

- **界面方式：**

  界面下载：https://github.com/rclone/rclone-webui-react

  加载命令：rclone rcd --rc-web-gui --rc-user=abc --rc-pass=abcd ./ui

  然后界面进行配置。

- **命令行方式：**

  **配置远程存储**：运行 `rclone config` 创建远程配置。rclone 支持多种后端类型（SFTP、S3、FTP、Google Drive 等）

  ```bash
  rclone config
  ```

  **SFTP 配置示例**：

  ```ini
  [route84]
  type = sftp
  host = 192.0.0.1
  user = xxxx
  pass = <obscured_password>  # 使用 rclone obscure 加密的密码
  shell_type = unix
  port = 22  # 可选，默认为 22
  ```

  **注意**：rclone 支持多种存储后端，您可以根据需要配置 SFTP、S3、FTP 等不同类型的远程存储。

3. **配置文件位置**：rclone 会自动查找配置文件，查找顺序：
   - 环境变量 `RCLONE_CONFIG` 指定的路径
   - 当前工作目录中的 `rclone.conf`
   - Python 脚本目录中的 `rclone.conf`
   - Windows: `%APPDATA%\rclone\rclone.conf`
   - Linux/Mac: `~/.config/rclone/rclone.conf` 或 `~/.rclone.conf`

### 配置 MCP 客户端

在 MCP 客户端配置文件中添加服务器配置（以 Claude Desktop 为例，配置文件通常位于 `~/Library/Application Support/Claude/claude_desktop_config.json` 或 Windows 的对应位置）：

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

**重要说明**：

- 将 `/path/to/cloud-builder` 替换为项目根目录的**绝对路径**
- `PROJECT_PATH` 环境变量用于指定当前工作项目目录，服务器会在此目录查找 `.cloudbuilder.json` 配置文件
- 服务器使用 stdio 传输，无需网络端口

## ⚙️ 配置方式

CloudBuilder 支持两种配置方式，**项目级配置优先于环境变量**。

### 1. 项目级配置（推荐）

在每个项目根目录创建 `.cloudbuilder.json` 文件：

```json
{
  "REMOTE_HOST_NAME": "route84",
  "LOCAL_PATH": "E:\\AI\\test_c",
  "REMOTE_PATH": "/home/xxxx/ftp_dir",
  "BUILD_COMMAND": "/home/xxxx/ftp_dir/build.sh"
}
```

**优点**：

- ✅ 每个项目可以有独立的配置
- ✅ 配置与项目代码一起管理（可提交到版本控制）
- ✅ 切换项目时自动使用对应配置

**查找逻辑**：服务器从 `PROJECT_PATH` 环境变量指定的目录查找 `.cloudbuilder.json` 文件。

### 2. 环境变量配置

在 MCP 客户端配置中设置环境变量：

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

### 配置项说明

| 配置项             | 描述                                       | 必需 | 说明                               |
| ------------------ | ------------------------------------------ | ---- | ---------------------------------- |
| `REMOTE_HOST_NAME` | rclone.conf 中的远程配置名称（如 route84） | ✅   | 必须与 rclone 配置中的名称完全匹配 |
| `RCLONE_EXE_PATH`  | rclone 执行文件的路径                      | ✅   | 可选，建议设置以验证路径有效性     |
| `LOCAL_PATH`       | 本地项目目录路径                           | ✅   | 用于文件同步的本地根目录           |
| `REMOTE_PATH`      | 远程服务器目录路径                         | ✅   | 用于文件同步的远程根目录           |
| `BUILD_COMMAND`    | 工程编译命令                               | ✅   | 可选，用于自动化构建工作流         |

**注意事项**：

- 远程连接信息（host、user、pass、port 等）从 rclone.conf 自动读取，无需在配置中设置
- 密码使用 rclone 的 obscure 算法加密/解密，无需手动处理
- rclone 支持多种后端类型（SFTP、S3、FTP 等），配置方式可能略有不同
- 同步忽略规则从项目的 `.sync_rules` 文件中读取（rclone 过滤格式）

### 同步忽略规则

在项目根目录创建 `.sync_rules` 文件，使用 rclone 过滤格式：

```
- .specstory/**
- .cursorindexingignore
- build/**
- *.log
- node_modules/**
```

## 🛠️ MCP 工具

### sync_directory

将本地目录同步到远程服务器（通过 rclone）。

**参数**：

- `local_dir`（可选）：本地目录路径，默认使用 `LOCAL_PATH` 配置
- `remote_dir`（可选）：远程目录路径，默认使用 `REMOTE_PATH` 配置
- `delete_excess`（可选）：是否删除目标中源不存在的文件，默认为 `true`

**返回**：包含同步结果的字典，包括：

- 上传的文件列表和统计
- 创建的目录列表
- 删除的文件列表（如果启用）
- 忽略的项目列表
- 错误信息（如果有）

**示例**：

```python
# 使用默认配置路径
sync_directory()

# 指定自定义路径
sync_directory("/custom/local/path", "/custom/remote/path")

# 禁用删除多余文件
sync_directory(delete_excess=False)
```

### upload_file

上传单个文件到远程服务器（通过 rclone）。

**参数**：

- `local_file_path`：要上传的本地文件路径（推荐使用绝对路径，或相对于 `LOCAL_PATH` 的相对路径）
- `remote_file_path`（可选）：远程目标路径，如果未指定则根据 `LOCAL_PATH`/`REMOTE_PATH` 映射自动确定

**返回**：包含上传结果的字典，包括文件大小和路径信息。

**示例**：

```python
# 自动确定远程路径（基于 LOCAL_PATH/REMOTE_PATH 映射）
upload_file("E:\\AI\\test_c\\main.c")

# 指定确切的远程目标路径
upload_file("E:\\AI\\test_c\\main.c", "/home/xxxx/ftp_dir/main.c")
```

### read_remote_file

从远程服务器读取文件内容（通过 rclone）。

**参数**：

- `remote_file_path`：要读取的远程文件路径
- `encoding`（可选）：文本编码格式，默认为 `utf-8`

**返回**：包含文件内容、大小和编码信息的字典。

**示例**：

```python
# 使用默认 UTF-8 编码读取
read_remote_file("/home/xxxx/ftp_dir/main.c")

# 指定编码格式
read_remote_file("/home/xxxx/ftp_dir/main.c", "latin-1")
```

### execute_remote_command

通过 SSH 在远程服务器上执行命令。

**参数**：

- `command`：要在远程服务器上执行的命令
- `working_directory`（可选）：命令的工作目录

**返回**：包含命令输出、退出代码、stdout 和 stderr 的字典。

**示例**：

```python
# 简单命令
execute_remote_command("ls -la")

# 带工作目录的命令
execute_remote_command("make clean", "/home/xxxx/ftp_dir")

# 执行构建命令
execute_remote_command("/home/xxxx/ftp_dir/build.sh")
```

### list_remote_directory

列出远程目录的内容（通过 rclone）。

**参数**：

- `remote_dir_path`：要列出的远程目录路径

**返回**：包含目录内容的字典，包括文件名、大小、权限和类型信息。

**示例**：

```python
list_remote_directory("/home/xxxx/ftp_dir")
```

## 📚 MCP 资源

### cloudbuilder://config

获取当前 CloudBuilder 服务器配置信息（不包含敏感数据如密码）。

**返回**：包含以下信息的 JSON：

- 连接状态（已配置/未完成）
- 远程服务器信息（主机、端口、用户名）
- 路径配置（本地路径、远程路径）
- 构建命令（如果已配置）
- 缺失或不完整的设置

## 💡 MCP 提示（工作流）

### check_config_workflow

检查 CloudBuilder 配置的工作流提示。指导如何：

1. 获取当前配置
2. 检查配置完整性
3. 报告缺失的配置项

### sync_workflow

文件同步工作流提示。提供将文件同步到远程服务器的分步指导。

### build_workflow

远程构建工作流提示。支持：

1. 在远程服务器上执行构建命令
2. 自动读取编译错误
3. 自动修复错误（最多 5 次尝试）
4. 将远程文件路径转换为本地路径进行修复

### sync_and_build_workflow

同步并构建的完整工作流提示。结合文件同步和自动化构建，包括：

1. 同步文件到远程服务器
2. 执行构建命令
3. 自动修复编译错误
4. 重复直到构建成功或达到最大尝试次数

## 🔒 安全考虑

- ✅ **Stdio 传输**：服务器使用 stdio 传输，消除了网络安全问题
- ✅ **密码加密**：远程凭据存储在 rclone.conf 中，使用 rclone 的 obscure 算法加密
- ✅ **自动解密**：密码自动解密，无需在环境变量中明文存储
- ✅ **敏感数据保护**：日志或响应中不会暴露敏感数据（如密码）
- ✅ **路径限制**：所有文件操作都限制在配置的路径内
- ✅ **SSH 安全**：SSH 连接使用 paramiko，具有适当的主机密钥处理
- ✅ **多后端支持**：通过 rclone 支持多种存储后端（SFTP、S3、FTP 等）

## 🐛 故障排除

### 连接问题

**问题**：无法连接到远程服务器

**解决方案**：

1. 验证 `REMOTE_HOST_NAME` 是否与 rclone.conf 中的远程配置名称完全匹配（区分大小写）
2. 检查 rclone.conf 配置文件是否存在且可读
3. 验证 rclone.conf 中的配置字段是否正确（根据后端类型，字段可能不同）
   - SFTP: `host`、`user`、`pass`、`port` 等
   - S3: `access_key_id`、`secret_access_key`、`region` 等
   - 其他后端请参考 rclone 文档
4. 如果配置中有 `port` 字段（如 SFTP），确保端口号正确（默认为 22）
5. 检查远程服务器是否可从您的网络访问
6. 使用 `rclone config show <remote_name>` 验证配置是否正确
7. 测试 rclone 连接：`rclone lsd <remote_name>:`

### 路径问题

**问题**：文件同步失败或路径错误

**解决方案**：

1. 验证 `LOCAL_PATH` 存在且可读
2. 确保 `REMOTE_PATH` 在远程服务器上存在且有写权限
3. 检查本地和远程系统的文件权限
4. 使用绝对路径而不是相对路径
5. 验证路径映射是否正确（`LOCAL_PATH` → `REMOTE_PATH`）

### 配置问题

**问题**：配置未生效或找不到配置文件

**解决方案**：

1. 检查 `PROJECT_PATH` 环境变量是否正确设置
2. 确认 `.cloudbuilder.json` 文件位于项目根目录
3. 验证 JSON 格式是否正确（可使用 JSON 验证工具）
4. 检查配置项名称拼写是否正确
5. 查看服务器日志以了解配置加载过程

### rclone 配置问题

**问题**：rclone 操作失败

**解决方案**：

1. 确保 rclone.conf 文件在可查找的位置（见上方配置文件位置说明）
2. 使用 `rclone config paths` 查看 rclone 的配置文件路径
3. 验证远程配置名称拼写正确（区分大小写）
4. 如果密码解密失败，检查 pass 字段（如适用）是否为有效的 obscure 加密值
5. 可以使用 `python src/rclone/rclone_decrypt_pass.py --remote <remote_name>` 测试配置读取
6. 如果设置了 `RCLONE_EXE_PATH`，验证路径是否存在且可执行
7. 根据使用的后端类型，确保所有必需的配置字段都已正确设置

### 同步忽略规则问题

**问题**：不应该同步的文件被同步了，或应该同步的文件被忽略了

**解决方案**：

1. 检查 `.sync_rules` 文件格式是否正确（rclone 过滤格式）
2. 模式支持 Unix 风格的通配符（`*`、`?`、`[]`）
3. 目录模式应以 `/` 结尾
4. 使用 `-` 前缀表示排除模式
5. 测试规则：`rclone ls <remote_name>:<remote_path> --filter-from .sync_rules`

### 构建命令问题

**问题**：构建命令执行失败

**解决方案**：

1. 验证 `BUILD_COMMAND` 路径是否正确
2. 确保构建命令在远程服务器上可执行
3. 检查远程服务器上的工作目录权限
4. 查看命令输出中的错误信息
5. 尝试手动在远程服务器上执行构建命令以验证

## 📝 使用示例

### 完整工作流示例

1. **检查配置**：

   ```
   使用 check_config_workflow 提示检查当前配置
   ```

2. **同步文件**：

   ```
   使用 sync_workflow 提示同步本地文件到远程服务器
   ```

3. **执行构建**：

   ```
   使用 build_workflow 提示在远程服务器上构建项目
   ```

4. **同步并构建**：

   ```
   使用 sync_and_build_workflow 提示完成同步和构建的完整流程
   ```

### 手动工具调用示例

```python
# 1. 同步整个项目目录
sync_directory()

# 2. 上传单个文件
upload_file("src/main.c")

# 3. 读取远程文件
read_remote_file("/home/xxxx/ftp_dir/src/main.c")

# 4. 执行构建命令
execute_remote_command("/home/xxxx/ftp_dir/build.sh", "/home/xxxx/ftp_dir")

# 5. 列出远程目录
list_remote_directory("/home/xxxx/ftp_dir")
```

---

**注意**：MCP 服务器通常不需要手动运行，它们由 MCP 客户端（如 Claude Desktop、Cursor）自动启动和管理。如果需要手动测试，可以使用：

```bash
uv run python src/main.py
```
