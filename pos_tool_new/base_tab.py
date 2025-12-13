import os
import sys
from typing import Tuple, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import (
    QWidget, QPushButton, QHBoxLayout,
    QLabel, QRadioButton, QButtonGroup, QGroupBox, QMainWindow,
    QToolButton, QMessageBox, QVBoxLayout
)


class BaseTabWidget(QWidget):
    """基础选项卡组件，提供通用功能"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(2)
        self.layout.setContentsMargins(3, 3, 3, 3)

    @staticmethod
    def create_warning_label(message: str) -> QLabel:
        """创建警告标签"""
        warn = QLabel(message)
        warn.setStyleSheet("""
            QLabel {
                color: #e74c3c;
                font-weight: bold;
                font-size: 12px;
                background-color: #ffebee;
                padding: 6px;
                border-radius: 3px;
                border: 1px solid #ffcdd2;
            }
        """)
        warn.setWordWrap(True)
        return warn

    def create_env_selector(self, default: str = "QA") -> Tuple[QWidget, QButtonGroup]:
        """创建环境选择器"""
        group = QButtonGroup()
        frame = QWidget()
        layout = QHBoxLayout(frame)
        layout.setSpacing(1)
        layout.setContentsMargins(2, 2, 2, 2)

        for name in ["PROD", "QA", "DEV"]:
            btn = QRadioButton(name)
            btn.setStyleSheet("QRadioButton { font-size: 11px; }")
            group.addButton(btn)
            layout.addWidget(btn)
            if name == default:
                btn.setChecked(True)

        layout.addStretch()
        return frame, group

    def get_selected_env(self, button_group: QButtonGroup) -> str:
        """获取选中的环境"""
        for btn in button_group.buttons():
            if btn.isChecked():
                return btn.text()
        return "QA"

    def add_help_button(self, parent_button: QPushButton, info: str):
        """为按钮添加帮助按钮"""
        help_btn = QToolButton()
        help_btn.setText("?")
        help_btn.setToolTip("点击查看使用说明")
        help_btn.clicked.connect(lambda: self.show_upgrade_help(info))

        help_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: 1px solid #999;
                border-radius: 8px;
                color: #555;
                font-weight: bold;
                font-size: 10px;
                padding: 0px;
            }
            QToolButton:hover {
                background: #ffeb3b;
                color: #333;
                border: 1px solid #ffc107;
            }
        """)
        help_btn.setFixedSize(20, 20)

        parent_button_layout = QHBoxLayout(parent_button)
        parent_button_layout.setContentsMargins(0, 0, 0, 0)
        parent_button_layout.addStretch()
        parent_button_layout.addWidget(help_btn)

    def show_upgrade_help(self, info: str):
        """显示升级帮助"""
        QMessageBox.information(self, "使用说明", info)

    def _find_mainwindow(self) -> Optional[QMainWindow]:
        """递归查找主窗口"""
        parent = self.parent()
        while parent is not None and not isinstance(parent, QMainWindow):
            parent = parent.parent()
        return parent

    def hide_main_log_area(self):
        """隐藏主窗口日志区域"""
        mainwin = self._find_mainwindow()
        if mainwin is not None:
            for gb in mainwin.findChildren(QGroupBox):
                if gb.title().strip() == "📝 操作日志":
                    gb.setVisible(False)
            if hasattr(mainwin, 'layout') and callable(mainwin.layout):
                mainwin.layout().activate()
            mainwin.update()

    def show_main_log_area(self):
        """显示主窗口日志区域"""
        mainwin = self._find_mainwindow()
        if mainwin is not None:
            for gb in mainwin.findChildren(QGroupBox):
                if gb.title().strip() == "📝 操作日志":
                    gb.setVisible(True)
            if hasattr(mainwin, 'layout') and callable(mainwin.layout):
                mainwin.layout().activate()
            mainwin.update()
