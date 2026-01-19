"""
应用入口模块
"""
import sys
import time

from PyQt6.QtWidgets import QApplication

from pos_tool_new.UI.main_window import MainWindow
from pos_tool_new.modern_splash import ModernSplashScreen
from pos_tool_new.utils.log_manager import global_log_manager


def create_main_window():
    """创建主窗口"""
    start_time = time.time()
    win = MainWindow()
    end_time = time.time()

    cost_ms = int((end_time - start_time) * 1000)
    global_log_manager.log(f"应用启动耗时: {cost_ms} ms", "info")

    return win


def main():
    """应用主入口"""
    app = QApplication(sys.argv)

    # 获取资源路径
    if hasattr(sys, '_MEIPASS'):
        resource_path = lambda relative_path: sys._MEIPASS + '/' + relative_path
    else:
        import os
        resource_path = lambda relative_path: os.path.join(os.path.abspath("."), relative_path)

    splash = ModernSplashScreen(resource_path('UI/loading.gif'), duration=1800)
    splash.start(create_main_window)
    sys.exit(app.exec())
