"""
日志工具模块
提供详细的调试信息输出
"""

import logging
import sys
import os
from datetime import datetime
from pathlib import Path


class Logger:
    """日志工具类"""
    
    def __init__(self, name: str = "pic2md", level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """设置日志处理器"""
        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # 创建文件处理器
        log_dir = Path.home() / ".pic2md" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"pic2md_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 创建格式化器
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 设置格式化器
        console_handler.setFormatter(console_formatter)
        file_handler.setFormatter(file_formatter)
        
        # 添加处理器
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
    def debug(self, message: str):
        """输出调试信息"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """输出一般信息"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """输出警告信息"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """输出错误信息"""
        self.logger.error(message)
    
    def critical(self, message: str):
        """输出严重错误信息"""
        self.logger.critical(message)
    
    def exception(self, message: str):
        """输出异常信息（包含堆栈跟踪）"""
        self.logger.exception(message)


# 全局日志实例
_logger = None


def get_logger() -> Logger:
    """获取全局日志实例"""
    global _logger
    if _logger is None:
        _logger = Logger()
    return _logger


def debug(message: str):
    """输出调试信息"""
    get_logger().debug(message)


def info(message: str):
    """输出一般信息"""
    get_logger().info(message)


def warning(message: str):
    """输出警告信息"""
    get_logger().warning(message)


def error(message: str):
    """输出错误信息"""
    get_logger().error(message)


def critical(message: str):
    """输出严重错误信息"""
    get_logger().critical(message)


def exception(message: str):
    """输出异常信息"""
    get_logger().exception(message)


def main():
    """测试日志功能"""
    logger = get_logger()
    
    logger.debug("这是一条调试信息")
    logger.info("这是一般信息")
    logger.warning("这是一条警告信息")
    logger.error("这是一条错误信息")
    
    try:
        1 / 0
    except Exception:
        logger.exception("这是一个异常示例")


if __name__ == "__main__":
    main()