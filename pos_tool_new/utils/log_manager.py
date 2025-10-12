# log_manager.py
import logging
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal

class LogManager(QObject):
    """
    统一的日志管理器，负责接收所有日志并分发到不同输出端（界面、文件等）。
    """
    log_received = pyqtSignal(str, str)  # (message, level)

    def __init__(self, parent=None):
        super().__init__(parent)
        # 可以在此配置Python标准库的logging，例如输出到文件
        self._setup_file_logging()

    def _setup_file_logging(self):
        """配置文件日志（可选）"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename='app.log',
            filemode='a'
        )
        self._logger = logging.getLogger(__name__)

    def log(self, message: str, level: str = "info"):
        """
        记录日志的主要方法。
        level: 'debug', 'info', 'success', 'warning', 'error'
        'success' 会被映射为 logging.INFO 级别（标准 logging 无 success 级别）。
        """
        # 1. 发送信号到UI（主线程）
        timestamp = datetime.now().strftime('%H:%M:%S')
        levels = {
            "info": ("\u2139\ufe0f", "#007bff"),
            "success": ("\u2705", "#28a745"),
            "warning": ("\u26a0\ufe0f", "#ffc107"),
            "error": ("\u274c", "#dc3545"),
            "debug": ("\ud83d\udd0d", "#6c757d")
        }
        icon, color = levels.get(level, ("\ud83d\udccc", "#6c757d"))
        formatted_message = f"[{timestamp}] {icon} {message}"
        # 发射信号，让UI更新日志框
        self.log_received.emit(formatted_message, color)

        # 2. 同时记录到文件（使用标准logging）
        # 'success' 不是标准日志级别，映射为 INFO
        if level.lower() == 'success':
            log_level = logging.INFO
        else:
            log_level = getattr(logging, level.upper(), logging.INFO)
        self._logger.log(log_level, message)

# 创建全局单例
global_log_manager = LogManager()