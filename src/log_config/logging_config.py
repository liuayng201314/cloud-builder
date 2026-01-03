import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from loguru import logger


def get_log_dir() -> Path:
    """
    获取日志目录路径
    
    Returns:
        Path: 日志目录路径，默认为 ~/.cloudbuilder/logs
    """
    return Path.home() / ".cloudbuilder" / "logs"


def should_rotate_log(log_file: Path) -> bool:
    """
    判断日志文件是否需要切割
    
    判断规则：文件的修改日期不是今天（即文件是昨天的或更早的）
    
    Args:
        log_file: 日志文件路径
        
    Returns:
        bool: 如果需要切割返回 True，否则返回 False
    """
    if not log_file.exists():
        return False
    
    # 获取文件的修改时间
    file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
    # 获取今天的日期（只比较日期部分，不比较时间）
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    file_date = file_mtime.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 如果文件的日期不是今天，则需要切割
    return file_date < today


def rotate_log_file_on_startup(log_file: Path, base_name: str) -> bool:
    """
    在程序启动时切割日志文件（如果文件是昨天的或更早的）
    
    Args:
        log_file: 日志文件路径
        base_name: 日志文件的基础名称（如 'app', 'err'）
        
    Returns:
        bool: 如果成功返回 True，否则返回 False
    """
    try:
        if not should_rotate_log(log_file):
            return False
        
        # 获取文件的修改时间，用于确定日期
        file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        date_str = file_mtime.strftime("%Y-%m-%d")
        
        # 生成新的文件名：app_2025-01-18.log
        new_name = f"{base_name}_{date_str}.log"
        new_path = log_file.parent / new_name
        
        # 如果目标文件已存在，添加序号
        counter = 1
        while new_path.exists():
            new_name = f"{base_name}_{date_str}_{counter}.log"
            new_path = log_file.parent / new_name
            counter += 1
        
        # 重命名文件
        log_file.rename(new_path)
        print(f"[成功] 程序启动时已切割日志文件: {log_file.name} -> {new_path.name}")
        
        # 创建新的空日志文件
        log_file.touch()
        
        return True
        
    except Exception as e:
        print(f"[警告] 切割日志文件失败 {log_file}: {e}")
        return False


def setup_logging(config_path: Optional[str] = None) -> None:
    """
    设置日志配置
    
    Args:
        config_path: 配置文件路径，如果为None则使用默认配置
    """
    # 默认配置
    default_config = {
        'console_level': 'DEBUG',
        'file_level': 'DEBUG',
        'rotation': '1 day',
        'retention': '1 week',
        'compression': 'zip',
        'max_file_size': '200 MB'
    }

    log_config = default_config.copy()

    # 尝试读取配置文件
    if config_path and Path(config_path).exists():
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            log_config.update(config.get('logging', {}))
        except Exception as e:
            print(f"Warning: Could not load logging config from {config_path}: {e}")
            print("Using default logging configuration")
    else:
        # 使用环境变量覆盖默认配置
        log_config.update({
            'console_level': os.getenv('LOG_CONSOLE_LEVEL', default_config['console_level']),
            'file_level': os.getenv('LOG_FILE_LEVEL', default_config['file_level']),
            'rotation': os.getenv('LOG_ROTATION', default_config['rotation']),
            'retention': os.getenv('LOG_RETENTION', default_config['retention']),
            'compression': os.getenv('LOG_COMPRESSION', default_config['compression']),
            'max_file_size': os.getenv('LOG_MAX_FILE_SIZE', default_config['max_file_size'])
        })

    # 确保日志目录存在
    log_dir = get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    # 移除默认处理器
    logger.remove()

    # 添加控制台处理器
    # CRITICAL: Disable colorize for MCP servers to prevent ANSI codes in JSON responses
    # MCP servers use stdio for communication, so colored output can break JSON parsing
    logger.add(
        sys.stderr,  # Use stderr instead of stdout to avoid interfering with MCP stdio communication
        level=log_config.get('console_level', 'INFO'),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        colorize=False  # Disable color to prevent ANSI codes in output
    )

    # 添加文件处理器 - 应用日志（排除错误日志）
    def app_log_filter(record):
        """应用日志过滤器，排除错误日志"""
        # 排除错误级别日志（错误日志单独记录）
        if record["level"].name == "ERROR":
            return False
        return True
    
    logger.add(
        str(log_dir / "app.log"),
        rotation=log_config.get('rotation', '1 day'),
        retention=log_config.get('retention', '1 week'),
        compression=log_config.get('compression', 'zip'),
        level=log_config.get('file_level', 'DEBUG'),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        enqueue=True,  # 异步写入，提高性能
        backtrace=True,  # 包含堆栈跟踪
        diagnose=True,  # 包含变量值
        filter=app_log_filter  # 应用日志过滤器
    )

    # 添加文件处理器 - 错误日志
    def error_log_filter(record):
        """错误日志过滤器"""
        return record["level"].name == "ERROR"
    
    logger.add(
        str(log_dir / "err.log"),
        rotation=log_config.get('rotation', '1 day'),
        retention=log_config.get('retention', '1 week'),
        compression=log_config.get('compression', 'zip'),
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        enqueue=True,
        backtrace=True,
        diagnose=True,
        filter=error_log_filter  # 错误日志过滤器
    )

    # 程序启动时：检查并切割昨天的日志文件
    log_files_to_rotate = {
        'app': log_dir / 'app.log',
        'err': log_dir / 'err.log'
    }
    
    for base_name, log_file in log_files_to_rotate.items():
        rotate_log_file_on_startup(log_file, base_name)


def get_logger(name: str = None):
    """
    获取logger实例
    
    Args:
        name: logger 名称
        
    Returns:
        loguru.Logger: 配置好的 logger 实例
    """
    if name:
        return logger.bind(name=name)
    else:
        return logger
