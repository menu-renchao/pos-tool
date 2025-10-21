from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QRadioButton, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, \
    QFormLayout, QMessageBox

from pos_tool_new.main import BaseTabWidget
from pos_tool_new.work_threads import DbConfigWorkerThread, DatabaseConnectThread
from .db_config_service import DbConfigService


class DbConfigWindow(BaseTabWidget):
    """
    数据库配置项 UI，包含筛选框、单选框、执行按钮。
    """

    def __init__(self, parent=None):
        super().__init__(title="数据库配置", parent=parent)
        self.service = DbConfigService()
        self.init_ui()

    def init_ui(self):
        # 主布局直接用 self.layout
        main_layout = self.layout
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # 数据库连接组
        db_group = QGroupBox("数据库连接")
        db_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 10px; }")
        db_layout = QFormLayout()
        db_layout.setContentsMargins(8, 12, 8, 12)
        db_layout.setSpacing(8)
        db_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

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

        db_row_layout = QHBoxLayout()
        db_row_layout.setContentsMargins(0, 0, 0, 0)
        db_row_layout.setSpacing(12)
        db_row_layout.addWidget(QLabel("主机地址:"))
        db_row_layout.addWidget(self.host_combo)
        db_row_layout.addWidget(QLabel("状态:"))
        db_row_layout.addWidget(self.status_label)
        db_row_layout.addWidget(self.connect_btn)
        db_row_layout.addStretch()
        db_layout.addRow(db_row_layout)

        db_group.setLayout(db_layout)
        main_layout.addWidget(db_group)

        # 配置项组
        config_group = QGroupBox("配置设置")
        config_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 10px; }")
        config_layout = QVBoxLayout()
        config_layout.setContentsMargins(8, 12, 8, 12)
        config_layout.setSpacing(10)

        # 配置项选择
        config_form_layout = QFormLayout()
        config_form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.combo = QComboBox()
        self.combo.addItems(['Cash discount'])  # 可扩展
        config_form_layout.addRow(QLabel('配置项:'), self.combo)
        config_layout.addLayout(config_form_layout)

        # 单选框组
        radio_group = QGroupBox("开关状态")
        radio_group.setStyleSheet("QGroupBox { font-weight: normal; font-size: 9px; }")
        radio_layout = QHBoxLayout()
        radio_layout.setContentsMargins(8, 8, 8, 8)

        self.radio_on = QRadioButton('打开')
        self.radio_off = QRadioButton('关闭')
        self.radio_on.setChecked(True)

        radio_layout.addWidget(self.radio_on)
        radio_layout.addWidget(self.radio_off)
        radio_layout.addStretch()
        radio_group.setLayout(radio_layout)
        config_layout.addWidget(radio_group)

        # 执行按钮
        self.btn_exec = QPushButton('执行配置')
        self.btn_exec.setFixedHeight(32)
        self.btn_exec.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 6px 12px;
                font-weight: bold;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #A5D6A7;
            }
        """)
        self.btn_exec.clicked.connect(self.on_execute)
        config_layout.addWidget(self.btn_exec)

        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)

        # 添加弹性空间
        main_layout.addStretch()

        # 设置主布局（已在 BaseTabWidget 构造函数设置，无需重复 setLayout）
        # self.setLayout(main_layout)

    def on_execute(self):
        config_name = self.combo.currentText()
        enabled = self.radio_on.isChecked()
        db_params = self.get_db_params()
        if hasattr(self, 'worker') and self.worker is not None and self.worker.isRunning():
            return
        self.worker = DbConfigWorkerThread(self.service, config_name, enabled, db_params)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.error_occurred.connect(self.on_worker_error)
        self.worker.finished_updated.connect(self.on_worker_result)
        self.worker.start()

    def on_worker_error(self, msg):
        self.log_message(msg, "error")

    def on_worker_result(self, success, msg):
        if success:
            self.log_message(msg, "success")
        else:
            self.log_message(msg, "error")

    def on_worker_finished(self):
        self.worker = None

    def get_db_params(self):
        return {
            'host': self.host_combo.currentText(),
            'port': 22108,  # 默认值
            'user': 'shohoku',
            'password': 'N0mur@4$99!',
            'database': 'kpos'  # 默认值
        }

    def log_message(self, message: str, level: str = "info"):
        """使用后端方法记录日志"""
        self.service.log(message, level)

    def on_connect_success(self, success, message):
        if success:
            self.status_label.setText("已连接")
            self.status_label.setStyleSheet("color: green; font-weight: normal;")
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
        self.db_thread.finished_updated.connect(self.on_connect_success)
        self.db_thread.error_occurred.connect(self.on_connect_error)
        self.db_thread.start()
