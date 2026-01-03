"""Configuration loader for CloudBuilder."""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from log_config.logging_config import get_logger
from rclone.rclone_decrypt_pass import get_remote_config

# Load environment variables
load_dotenv()

logger = get_logger("CloudBuilder.Config")


def _load_project_config() -> Dict[str, Any]:
    """
    Load project-specific configuration from .cloudbuilder.json file.
    Only searches in PROJECT_PATH directory (project_dir/.cloudbuilder.json).
    
    Returns:
        Dictionary with project configuration, or empty dict if not found
    """
    config = {}
    
    # 只从 PROJECT_PATH 环境变量获取项目目录（Cursor打开的项目目录）
    project_path_env = os.environ.get("PROJECT_PATH")
    
    if not project_path_env:
        logger.info("PROJECT_PATH 环境变量未设置，跳过项目配置文件查找，将使用环境变量")
        return config
    
    # 如果 PROJECT_PATH 包含变量占位符（如 ${workspaceFolder}），说明变量未被替换，跳过
    if "${" in project_path_env or "$(" in project_path_env:
        logger.info(f"PROJECT_PATH 包含未替换的变量占位符: {project_path_env}，跳过项目配置文件查找，将使用环境变量")
        return config
    
    # 验证路径是否存在
    project_path = Path(project_path_env).resolve()
    if not project_path.exists():
        logger.warning(f"PROJECT_PATH 指定的路径不存在: {project_path_env}，跳过项目配置文件查找，将使用环境变量")
        return config
    
    if not project_path.is_dir():
        logger.warning(f"PROJECT_PATH 指定的路径不是目录: {project_path_env}，跳过项目配置文件查找，将使用环境变量")
        return config
    
    project_dir = project_path
    logger.info(f"从环境变量 PROJECT_PATH 获取项目目录: {project_dir}")
    logger.info(f"项目目录绝对路径: {project_dir.resolve()}")
    
    # 只在项目目录查找 .cloudbuilder.json
    config_file = project_dir / ".cloudbuilder.json"
    config_file_str = str(config_file)
    logger.info(f"查找项目配置文件: {config_file_str}")
    
    if config_file.exists():
        logger.info(f"找到配置文件: {config_file_str}")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"成功读取项目配置文件: {config_file_str}")
            logger.debug(f"配置文件内容: {json.dumps(config, indent=2, ensure_ascii=False)}")
            return config
        except json.JSONDecodeError as e:
            logger.warning(f"项目配置文件格式错误 {config_file_str}: {e}")
            return {}
        except Exception as e:
            logger.warning(f"读取项目配置文件失败 {config_file_str}: {e}", exc_info=True)
            return {}
    else:
        logger.info(f"项目配置文件不存在: {config_file_str}，将使用环境变量")
        return config


def _get_config_value(key: str, project_config: Dict[str, Any], env_key: str = None) -> Optional[str]:
    """
    Get configuration value from project config or environment variable.
    
    Args:
        key: Key name in project config
        project_config: Project configuration dictionary
        env_key: Environment variable key (defaults to key if not specified)
    
    Returns:
        Configuration value or None
    """
    env_key = env_key or key
    # Priority: project config > environment variable
    return project_config.get(key) or os.environ.get(env_key)


class Config:
    """Configuration class for CloudBuilder."""
    
    def __init__(self):
        """Initialize configuration from project config and environment variables."""
        # Load project configuration
        project_config = _load_project_config()
        
        # Configuration from project config (priority) or environment variables
        self.REMOTE_HOST_NAME = _get_config_value("REMOTE_HOST_NAME", project_config)
        self.RCLONE_EXE_PATH = _get_config_value("RCLONE_EXE_PATH", project_config)
        self.LOCAL_PATH = _get_config_value("LOCAL_PATH", project_config)
        self.REMOTE_PATH = _get_config_value("REMOTE_PATH", project_config)
        self.BUILD_COMMAND = _get_config_value("BUILD_COMMAND", project_config)
        
        # Log rclone executable path if set
        if self.RCLONE_EXE_PATH:
            logger.info(f"RCLONE_EXE_PATH 已设置: {self.RCLONE_EXE_PATH}")
            # 验证路径是否存在
            if not os.path.exists(self.RCLONE_EXE_PATH):
                logger.warning(f"RCLONE_EXE_PATH 指定的路径不存在: {self.RCLONE_EXE_PATH}")
        
        # Get remote configuration from rclone.conf
        self.TARGET_HOST = None
        self.TARGET_PORT = 22
        self.TARGET_USERNAME = None
        self.TARGET_PASSWORD = None
        
        if self.REMOTE_HOST_NAME:
            try:
                remote_config = get_remote_config(remote_name=self.REMOTE_HOST_NAME)
                self.TARGET_HOST = remote_config.get("host")
                self.TARGET_USERNAME = remote_config.get("user")
                self.TARGET_PASSWORD = remote_config.get("pass")
                # 如果配置中有port字段，使用它；否则使用默认值22
                if "port" in remote_config:
                    try:
                        self.TARGET_PORT = int(remote_config.get("port", 22))
                    except (ValueError, TypeError):
                        self.TARGET_PORT = 22
                logger.info(f"从rclone配置加载远程配置: {self.REMOTE_HOST_NAME}")
            except Exception as e:
                logger.error(f"无法从rclone配置加载远程配置 {self.REMOTE_HOST_NAME}: {e}")
                raise
        else:
            logger.warning("REMOTE_HOST_NAME环境变量未设置，无法加载rclone配置")


def load_config() -> Config:
    """
    Load and return configuration.
    
    Returns:
        Config instance with all configuration values
    """
    return Config()

