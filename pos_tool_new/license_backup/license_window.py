import os
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QVBoxLayout, QGroupBox, QFormLayout, QComboBox,
                             QLabel, QPushButton, QMessageBox, QFileDialog,
                             QHBoxLayout)

from pos_tool_new.license_backup.license_service import LicenseService
from pos_tool_new.main import BaseTabWidget


class DatabaseConnectThread(QThread):
    success_signal = pyqtSignal(bool, str)
    error_signal = pyqtSignal(str)

    def __init__(self, license_service, host):
        super().__init__()
        self.license_service = license_service
        self.host = host

    def run(self):
        try:
            success, message = self.license_service.connect_database(self.host)
            self.success_signal.emit(success, message)
        except Exception as e:
            self.error_signal.emit(str(e))


class LicenseToolTabWidget(BaseTabWidget):
    """License备份恢复工具 - 紧凑优化版"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = LicenseService()
        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("License备份恢复工具")

        # 设置全局字体
        font = QFont()
        font.setPointSize(9)
        self.setFont(font)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # 数据库连接组
        db_group = QGroupBox("数据库连接")
        db_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 10px; }")
        db_layout = QFormLayout()
        db_layout.setContentsMargins(8, 12, 8, 12)
        db_layout.setSpacing(8)
        db_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)  # 修正这里

        self.host_combo = QComboBox()
        self.host_combo.addItems([
            "192.168.0.", "192.168.1.", "10.24.1.",
            "10.1.10.", "10.0.10.", "192.168.252.", "192.168.253."
        ])
        self.host_combo.setEditable(True)
        self.host_combo.setFixedWidth(180)

        self.status_label = QLabel("未连接")
        self.status_label.setStyleSheet("color: gray; font-weight: normal;")

        self.connect_btn = QPushButton("连接")
        self.connect_btn.setFixedWidth(80)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 4px 8px;
                font-weight: bold;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BBDEFB;
            }
        """)
        self.connect_btn.clicked.connect(self.connect_database)

        db_layout.addRow("主机地址:", self.host_combo)
        db_layout.addRow("状态:", self.status_label)
        db_layout.addRow("", self.connect_btn)

        db_group.setLayout(db_layout)
        main_layout.addWidget(db_group)

        # 操作按钮组
        btn_group = QGroupBox("操作")
        btn_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 10px; }")
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(8, 12, 8, 12)
        btn_layout.setSpacing(8)

        self.backup_btn = QPushButton("备份")
        self.backup_btn.setFixedWidth(80)
        self.backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 4px 8px;
                font-weight: bold;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:pressed {
                background-color: #2E7D32;
            }
            QPushButton:disabled {
                background-color: #C8E6C9;
            }
        """)
        self.backup_btn.clicked.connect(self.backup_license)
        self.backup_btn.setEnabled(False)

        self.restore_btn = QPushButton("恢复")
        self.restore_btn.setFixedWidth(80)
        self.restore_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 4px 8px;
                font-weight: bold;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #E65100;
            }
            QPushButton:disabled {
                background-color: #FFE0B2;
            }
        """)
        self.restore_btn.clicked.connect(self.restore_license)
        self.restore_btn.setEnabled(False)

        btn_layout.addStretch()
        btn_layout.addWidget(self.backup_btn)
        btn_layout.addWidget(self.restore_btn)
        btn_layout.addStretch()

        btn_group.setLayout(btn_layout)
        main_layout.addWidget(btn_group)
        main_layout.addStretch(1)

        # 设置主布局
        self.layout.addLayout(main_layout)

    def log_message(self, message: str, level: str = "info"):
        """使用后端方法记录日志"""
        self.service.log(message, level)

    def connect_database(self):
        """连接数据库"""
        host = self.host_combo.currentText().strip()
        if not host:
            QMessageBox.warning(self, "警告", "请输入主机地址")
            return

        self.log_message(f"正在连接数据库: {host}", "info")
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("连接中...")

        self.db_thread = DatabaseConnectThread(self.service, host)
        self.db_thread.success_signal.connect(self.on_connect_success)
        self.db_thread.error_signal.connect(self.on_connect_error)
        self.db_thread.finished.connect(self.on_connect_finished)
        self.db_thread.start()

    def on_connect_success(self, success, message):
        if success:
            self.status_label.setText("已连接")
            self.status_label.setStyleSheet("color: green; font-weight: normal;")
            self.backup_btn.setEnabled(True)
            self.restore_btn.setEnabled(True)
            self.log_message(message, "success")
        else:
            self.status_label.setText("连接失败")
            self.status_label.setStyleSheet("color: red; font-weight: normal;")
            self.log_message(f"连接失败: {message}", "error")
            QMessageBox.warning(self, "连接失败", message)

    def on_connect_error(self, error_message):
        self.log_message(f"连接异常: {error_message}", "error")
        QMessageBox.critical(self, "错误", f"连接异常: {error_message}")

    def on_connect_finished(self):
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("连接")

    def backup_license(self):
        """备份License"""
        save_path = QFileDialog.getExistingDirectory(
            self, "选择保存目录", str(Path.home())
        )

        if not save_path:
            return

        self.service.strDBpath = os.path.join(save_path, "")
        self.log_message(f"开始备份License到: {save_path}")
        self.backup_btn.setEnabled(False)
        self.backup_btn.setText("备份中...")

        try:
            success, message = self.service.backup_license(
                self.host_combo.currentText()
            )

            if success:
                self.log_message("License备份成功", "success")
                QMessageBox.information(self, "成功", message)
            else:
                self.log_message(f"备份失败: {message}")
                QMessageBox.warning(self, "备份失败", message)

        except Exception as e:
            self.log_message(f"备份异常: {str(e)}", "error")
            QMessageBox.critical(self, "错误", f"备份异常: {str(e)}")
        finally:
            self.backup_btn.setEnabled(True)
            self.backup_btn.setText("备份")

    def restore_license(self):
        """恢复License"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择License文件", "", "SQL Files (*.sql);;All Files (*)"
        )

        if not file_path:
            return

        reply = QMessageBox.question(
            self, "确认恢复",
            f"确定要恢复License文件吗？\n{file_path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.log_message(f"开始恢复License: {file_path}", "info")
        self.restore_btn.setEnabled(False)
        self.restore_btn.setText("恢复中...")

        try:
            success, message = self.service.restore_license(
                self.host_combo.currentText(),
                file_path
            )

            if success:
                self.log_message("License恢复成功", "success")
                QMessageBox.information(self, "成功", message)
            else:
                self.log_message(f"恢复失败: {message}", "error")
                QMessageBox.warning(self, "恢复失败", message)

        except Exception as e:
            self.log_message(f"恢复异常: {str(e)}", "error")
            QMessageBox.critical(self, "错误", f"恢复异常: {str(e)}")
        finally:
            self.restore_btn.setEnabled(True)
            self.restore_btn.setText("恢复")
