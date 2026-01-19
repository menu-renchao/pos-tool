"""
主窗口日志区域模块
"""
from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton

from pos_tool_new.UI.styles import get_clear_button_style
from pos_tool_new.UI.widgets import EnhancedTextEdit


def create_log_area(window) -> tuple:
    """创建日志区域，返回 (log_group, log_text)"""
    log_group = QGroupBox("📝 操作日志")
    log_layout = QVBoxLayout(log_group)
    log_layout.setSpacing(4)
    log_layout.setContentsMargins(6, 6, 6, 6)

    # 日志工具栏
    log_toolbar = QHBoxLayout()
    log_toolbar.addStretch()

    clear_btn = QPushButton("🗑️ 清除日志")
    clear_btn.setMaximumWidth(100)
    clear_btn.clicked.connect(window.clear_logs)
    clear_btn.setStyleSheet(get_clear_button_style())
    log_toolbar.addWidget(clear_btn)
    log_layout.addLayout(log_toolbar)

    # 日志文本区域
    log_text = EnhancedTextEdit()
    if log_text is not None:
        log_text.setMinimumHeight(120)
    log_layout.addWidget(log_text)

    return log_group, log_text
