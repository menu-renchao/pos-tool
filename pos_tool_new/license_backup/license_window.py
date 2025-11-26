import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QVBoxLayout, QGroupBox, QFormLayout, QComboBox,
                             QLabel, QPushButton, QMessageBox, QFileDialog,
                             QHBoxLayout)

from pos_tool_new.license_backup.license_service import LicenseService
from pos_tool_new.main import BaseTabWidget
from pos_tool_new.work_threads import DatabaseConnectThread


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
        db_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.host_ip = QComboBox()
        self.host_ip.addItems([
            "192.168.0.", "192.168.1.", "10.24.1.",
            "10.1.10.", "10.0.10.", "192.168.252.", "192.168.253."
        ])
        self.host_ip.setEditable(True)
        self.host_ip.setFixedWidth(180)

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

        # 水平布局一行显示主机地址、状态、连接按钮
        db_row_layout = QHBoxLayout()
        db_row_layout.setContentsMargins(0, 0, 0, 0)
        db_row_layout.setSpacing(12)
        db_row_layout.addWidget(QLabel("主机地址:"))
        db_row_layout.addWidget(self.host_ip)
        db_row_layout.addWidget(QLabel("状态:"))
        db_row_layout.addWidget(self.status_label)
        db_row_layout.addWidget(self.connect_btn)
        db_row_layout.addStretch()
        db_layout.addRow(db_row_layout)

        db_group.setLayout(db_layout)
        main_layout.addWidget(db_group)

        # 店铺license相关操作按钮组
        btn_group = QGroupBox("店铺license")
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

        # app license相关操作按钮组
        app_license_group = QGroupBox("app license")
        app_license_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 10px; }")
        app_license_layout = QHBoxLayout()
        app_license_layout.setContentsMargins(8, 12, 8, 12)
        app_license_layout.setSpacing(8)

        self.expand_btn = QPushButton("扩充app license")
        self.expand_btn.setFixedWidth(120)
        self.expand_btn.clicked.connect(self.expand_app_license)
        self.expand_btn.setToolTip(
            " 用于扩充app license的数量：E-Menu License : 50, Tablet POS License : 50, Phone POS License : 20,\n Max number of kitchen display instance allowed : 50, POS iOS License : 50, POS Android License : 50, Kiosk License : 50, POS License : 50")
        self.expand_btn.setEnabled(False)
        app_license_layout.addStretch()
        app_license_layout.addWidget(self.expand_btn)
        app_license_layout.addStretch()
        app_license_group.setLayout(app_license_layout)

        # 两个分组并排放在一行
        group_h_layout = QHBoxLayout()
        group_h_layout.setContentsMargins(0, 0, 0, 0)
        group_h_layout.setSpacing(16)
        group_h_layout.addWidget(btn_group)
        group_h_layout.addWidget(app_license_group)
        main_layout.addLayout(group_h_layout)
        main_layout.addStretch(1)

        # 设置主布局
        self.layout.addLayout(main_layout)

    def log_message(self, message: str, level: str = "info"):
        """使用后端方法记录日志"""
        self.service.log(message, level)

    def connect_database(self):
        """连接数据库"""
        host = self.host_ip.currentText().strip()
        if not host:
            QMessageBox.warning(self, "警告", "请输入主机地址")
            return

        self.log_message(f"正在连接数据库: {host}", "info")
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("连接中...")

        self.db_thread = DatabaseConnectThread(self.service, host)
        self.db_thread.finished_updated.connect(self.on_connect_success)
        self.db_thread.error_occurred.connect(self.on_connect_error)
        self.db_thread.start()

    def on_connect_success(self, success, message):
        if success:
            self.status_label.setText(f"{message}")
            self.status_label.setStyleSheet("color: green; font-weight: normal;")
            self.backup_btn.setEnabled(True)
            self.restore_btn.setEnabled(True)
            self.expand_btn.setEnabled(True)
            self.log_message(message, "success")
        else:
            self.status_label.setText("连接失败")
            self.status_label.setStyleSheet("color: red; font-weight: normal;")
            self.log_message(f"连接失败: {message}", "error")
            QMessageBox.warning(self, "连接失败", message)
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("连接")

    def on_connect_error(self, error_message):
        self.log_message(f"连接异常: {error_message}", "error")
        QMessageBox.critical(self, "错误", f"连接异常: {error_message}")

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
                self.host_ip.currentText()
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
                self.host_ip.currentText(),
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

    def expand_app_license(self):
        """扩充app license"""
        host = self.host_ip.currentText().strip()
        if not host:
            QMessageBox.warning(self, "警告", "请输入主机地址")
            return
        self.expand_btn.setEnabled(False)
        self.expand_btn.setText("处理中...")
        self.log_message(f"扩充app license: {host}", "info")
        try:
            success, message = self.service.expand_app_license(host)
            if success:
                self.log_message("扩充app license成功", "success")
                self.log_message("需要重启后生效", "warning")
                QMessageBox.information(self, "成功", message)
            else:
                self.log_message(f"扩充失败: {message}", "error")
                QMessageBox.warning(self, "扩充失败", message)
        except Exception as e:
            self.log_message(f"扩充异常: {str(e)}", "error")
            QMessageBox.critical(self, "错误", f"扩充异常: {str(e)}")
        finally:
            self.expand_btn.setEnabled(True)
            self.expand_btn.setText("扩充app license")

    def set_host_ip(self, ip: str):
        """同步设置主机IP到host_ip输入框"""
        if self.host_ip:
            self.host_ip.setCurrentText(ip)
