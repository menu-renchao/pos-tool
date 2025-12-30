import os
from typing import Optional, Tuple, Callable

from PyQt6.QtCore import QTimer, pyqtSlot
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QLineEdit, QFileDialog, QGroupBox, QComboBox, QMessageBox,
    QInputDialog, QDialog, QListWidget, QListWidgetItem, QDialogButtonBox, QGridLayout
)

from pos_tool_new.backend import Backend
from pos_tool_new.base_tab import BaseTabWidget
from pos_tool_new.linux_pos.linux_service import LinuxService
from pos_tool_new.main import MainWindow
from pos_tool_new.work_threads import ReplaceWarThreadLinux, RestartPosThreadLinux, RestartTomcatThread, UpgradeThread, \
    UploadUpgradePackageThread, SshTestThread


class LinuxTabWidget(BaseTabWidget):
    """Linux选项卡组件"""

    def __init__(self, parent: Optional[MainWindow] = None):
        super().__init__("Linux POS")
        self.pipeline_upgrade_package_btn: Optional[QPushButton] = None
        self.upgrade_package_btn: Optional[QPushButton] = None
        self.status_label = None
        self.host_ip: Optional[QComboBox] = None
        self.username: Optional[QLineEdit] = None
        self.password: Optional[QLineEdit] = None
        self.ssh_group: Optional[QGroupBox] = None
        self.modify_btn: Optional[QPushButton] = None
        self.env_group: Optional[QGroupBox] = None
        self.test_btn: Optional[QPushButton] = None
        self.remote_md5_btn: Optional[QPushButton] = None
        self.download_log_btn: Optional[QPushButton] = None
        self.war_path: Optional[QLineEdit] = None
        self.local_md5_btn: Optional[QPushButton] = None
        self.replace_btn: Optional[QPushButton] = None
        self.upload_updater_btn: Optional[QPushButton] = None
        self.pipeline_upgrade_btn: Optional[QPushButton] = None
        self.restart_tomcat_btn: Optional[QPushButton] = None
        self.restart_btn: Optional[QPushButton] = None

        self.parent_window: Optional[MainWindow] = parent
        self.service = LinuxService()
        if self.parent_window:
            self.service.log_signal.connect(self.parent_window.append_log)
        self.setup_ui()

        # 初始化线程变量
        self.replace_thread: Optional[ReplaceWarThreadLinux] = None
        self.restart_thread: Optional[RestartPosThreadLinux] = None
        self.restart_tomcat_thread: Optional[RestartTomcatThread] = None
        self.upgrade_thread: Optional[UpgradeThread] = None
        self.upload_thread: Optional[UploadUpgradePackageThread] = None

    def _validate_connection_params(self) -> Tuple[bool, str, str, str, str]:
        """
        验证连接参数的有效性

        Returns:
            Tuple[bool, str, str, str, str]: (是否有效, 错误消息, 主机IP, 用户名, 密码)
        """
        if not all([self.host_ip, self.username, self.password]):
            return False, "SSH连接参数未初始化", "", "", ""

        host = self.host_ip.currentText().strip()
        username = self.username.text().strip()
        password = self.password.text().strip()

        # 验证IP地址格式
        if not host or host.endswith('.') or len(host.split('.')) != 4:
            return False, "请填写完整的主机IP地址！\n例如：192.168.0.100", host, username, password

        # 验证IP地址各部分是否有效
        ip_parts = host.split('.')
        for part in ip_parts:
            if not part.isdigit() or not 0 <= int(part) <= 255:
                return False, "请填写有效的主机IP地址！", host, username, password

        if not username:
            return False, "请填写用户名！", host, username, password

        if not password:
            return False, "请填写密码！", host, username, password

        return True, "", host, username, password

    def _validate_file_path(self, file_path: str, file_type: str = "文件") -> Tuple[bool, str]:
        """
        验证文件路径的有效性

        Args:
            file_path: 文件路径
            file_type: 文件类型描述

        Returns:
            Tuple[bool, str]: (是否有效, 错误消息)
        """
        if not file_path:
            return False, f"请先选择本地{file_type}文件！"

        if not os.path.isfile(file_path):
            return False, f"选择的{file_type}文件不存在或无效！"

        return True, ""

    def _execute_with_connection_validation(self, operation_name: str, callback: Callable,
                                            need_file_validation: bool = False,
                                            file_path: str = None,
                                            file_type: str = "文件") -> None:
        """
        执行需要连接验证的操作

        Args:
            operation_name: 操作名称（用于日志）
            callback: 验证通过后的回调函数
            need_file_validation: 是否需要文件验证
            file_path: 需要验证的文件路径
            file_type: 文件类型描述
        """
        try:
            # 验证连接参数
            is_valid, error_msg, host, username, password = self._validate_connection_params()
            if not is_valid:
                QMessageBox.warning(self, "参数错误", error_msg)
                return

            # 如果需要文件验证
            if need_file_validation and file_path:
                is_file_valid, file_error_msg = self._validate_file_path(file_path, file_type)
                if not is_file_valid:
                    QMessageBox.warning(self, "提示", file_error_msg)
                    return

            # 执行回调函数
            callback(host, username, password)

        except Exception as e:
            error_msg = f"{operation_name}过程中出错: {str(e)}"
            self.service.log(error_msg, level="error")
            QMessageBox.critical(self, "错误", error_msg)
            import traceback
            traceback.print_exc()

    def setup_ui(self):
        # 主布局设置
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(15, 15, 15, 15)

        # ========== 第一行：SSH连接设置 ==========
        ssh_group = QGroupBox("SSH连接设置")
        ssh_main_layout = QHBoxLayout(ssh_group)
        ssh_main_layout.setSpacing(10)

        # IP地址
        ip_layout = QHBoxLayout()
        ip_label = QLabel("主机IP:")
        self.host_ip = QComboBox()
        self.host_ip.addItems([
            "192.168.0.", "192.168.1.", "10.24.1.",
            "10.1.10.", "10.0.10.", "192.168.252.", "192.168.253."
        ])
        self.host_ip.setEditable(True)
        self.host_ip.setFixedWidth(120)
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.host_ip)
        ssh_main_layout.addLayout(ip_layout)

        # 用户名
        user_layout = QHBoxLayout()
        username_label = QLabel("用户名:")
        self.username = QLineEdit("menu")
        self.username.setFixedWidth(100)
        user_layout.addWidget(username_label)
        user_layout.addWidget(self.username)
        ssh_main_layout.addLayout(user_layout)

        # 密码
        pwd_layout = QHBoxLayout()
        password_label = QLabel("密码:")
        self.password = QLineEdit("M2ei#a$19!")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setFixedWidth(100)
        pwd_layout.addWidget(password_label)
        pwd_layout.addWidget(self.password)
        ssh_main_layout.addLayout(pwd_layout)

        # 测试连接按钮
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self.on_test_ssh)
        self.test_btn.setFixedWidth(100)
        ssh_main_layout.addWidget(self.test_btn)

        # 状态标签
        self.status_label = QLabel("连接状态未检测")
        self.status_label.setStyleSheet("color: red;")
        self.status_label.setFixedWidth(150)
        ssh_main_layout.addWidget(self.status_label)

        ssh_main_layout.addStretch()
        self.layout.addWidget(ssh_group)

        # ========== 第二行：文件操作 ==========
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(10)

        # 文件选择 (1/2)
        file_group = QGroupBox("换包/升级服务")
        file_main_layout = QVBoxLayout(file_group)
        file_main_layout.setContentsMargins(5, 10, 5, 10)

        # 文件路径选择
        path_layout = QHBoxLayout()
        self.war_path = QLineEdit()
        self.war_path.setPlaceholderText("请选择war文件路径...")
        path_layout.addWidget(self.war_path)

        btn_browse = QPushButton("选择...")
        btn_browse.clicked.connect(self.browse_war_file)
        btn_browse.setFixedWidth(80)
        path_layout.addWidget(btn_browse)

        btn_download_net = QPushButton("下载")
        btn_download_net.clicked.connect(self.download_war_from_net)
        btn_download_net.setFixedWidth(80)
        path_layout.addWidget(btn_download_net)

        file_main_layout.addLayout(path_layout)
        row2_layout.addWidget(file_group, 1)

        self.layout.addLayout(row2_layout)

        # ========== 第三行：主要操作按钮 ==========
        row3_layout = QHBoxLayout()
        row3_layout.setSpacing(10)

        # 文件操作按钮
        ops_group = QGroupBox("文件/查询操作")
        ops_layout = QVBoxLayout(ops_group)
        ops_layout.setContentsMargins(5, 10, 5, 10)

        # 第一行按钮
        ops_row1 = QHBoxLayout()
        self.replace_btn = QPushButton("替换war包")
        self.replace_btn.clicked.connect(self.on_replace_war_linux)
        ops_row1.addWidget(self.replace_btn)

        self.upload_updater_btn = QPushButton("上传升级包")
        self.upload_updater_btn.clicked.connect(self.on_upload_upgrade_package)
        self.upload_updater_btn.setToolTip("上传到/home/menu并解压")
        ops_row1.addWidget(self.upload_updater_btn)

        self.upgrade_package_btn = QPushButton("使用升级包")
        self.upgrade_package_btn.clicked.connect(self.on_upgrade_with_package)
        self.upgrade_package_btn.setToolTip("扫描/home/menu下的升级工具")
        ops_row1.addWidget(self.upgrade_package_btn)

        # 第二行按钮
        ops_row2 = QHBoxLayout()
        self.local_md5_btn = QPushButton("本地MD5")
        self.local_md5_btn.clicked.connect(self.on_check_local_md5)
        ops_row2.addWidget(self.local_md5_btn)

        self.remote_md5_btn = QPushButton("远程MD5")
        self.remote_md5_btn.clicked.connect(self.on_check_remote_md5)
        ops_row2.addWidget(self.remote_md5_btn)

        self.remote_app_btn = QPushButton("壳子版本")
        self.remote_app_btn.clicked.connect(self.on_get_app_version)
        ops_row2.addWidget(self.remote_app_btn)

        ops_layout.addLayout(ops_row1)
        ops_layout.addLayout(ops_row2)
        row3_layout.addWidget(ops_group, 2)

        # 重启操作
        restart_group = QGroupBox("重启/数据备份操作")
        restart_layout = QGridLayout(restart_group)
        restart_layout.setContentsMargins(5, 10, 5, 10)

        self.restart_tomcat_btn = QPushButton("重启Tomcat")
        self.restart_tomcat_btn.clicked.connect(self.on_restart_tomcat)
        restart_layout.addWidget(self.restart_tomcat_btn, 0, 0)

        self.restart_btn = QPushButton("重启POS")
        self.restart_btn.clicked.connect(self.on_restart_pos_linux)
        restart_layout.addWidget(self.restart_btn, 0, 1)

        self.backup_btn = QPushButton("数据备份")
        self.backup_btn.clicked.connect(self.on_backup_data)
        restart_layout.addWidget(self.backup_btn, 1, 0)

        self.restore_btn = QPushButton("数据恢复")
        self.restore_btn.clicked.connect(self.on_restore_data)
        restart_layout.addWidget(self.restore_btn, 1, 1)

        row3_layout.addWidget(restart_group, 1)
        self.layout.addLayout(row3_layout)

        # ========== 第四行：流水线和日志 ==========
        row4_layout = QHBoxLayout()
        row4_layout.setSpacing(10)

        # 流水线操作
        pipeline_group = QGroupBox("流水线")
        pipeline_layout = QHBoxLayout(pipeline_group)
        pipeline_layout.setContentsMargins(5, 10, 5, 10)

        # 环境选择（只在流水线里）
        env_group = QGroupBox()
        env_group.setTitle("配置文件环境选择")
        env_layout = QHBoxLayout(env_group)
        env_layout.setContentsMargins(5, 10, 5, 10)
        env_frame, self.env_group = self.create_env_selector("QA")
        env_layout.addWidget(env_frame)
        env_layout.addStretch()
        pipeline_layout.addWidget(env_group)

        self.pipeline_upgrade_btn = QPushButton("一键升级(war包)")
        self.pipeline_upgrade_btn.setToolTip("替换war包->修改文件->重启POS")
        self.pipeline_upgrade_btn.clicked.connect(self.on_pipeline_upgrade)
        pipeline_layout.addWidget(self.pipeline_upgrade_btn)

        self.pipeline_upgrade_package_btn = QPushButton("一键升级(升级包)")
        self.pipeline_upgrade_package_btn.setToolTip("使用升级包->修改文件->重启POS")
        self.pipeline_upgrade_package_btn.clicked.connect(self.on_pipeline_package_upgrade)
        pipeline_layout.addWidget(self.pipeline_upgrade_package_btn)

        row4_layout.addWidget(pipeline_group, 1)

        # 日志操作
        log_group = QGroupBox("日志管理")
        log_layout = QHBoxLayout(log_group)
        log_layout.setContentsMargins(5, 10, 5, 10)

        self.download_log_btn = QPushButton("下载日志")
        self.download_log_btn.clicked.connect(self.on_download_log)
        log_layout.addWidget(self.download_log_btn)

        self.tail_log_btn = QPushButton("实时日志")
        self.tail_log_btn.clicked.connect(self.on_tail_log_clicked)
        log_layout.addWidget(self.tail_log_btn)

        row4_layout.addWidget(log_group, 1)

        self.layout.addLayout(row4_layout)

        # 添加连接信号
        self.host_ip.currentTextChanged.connect(self.reset_connection_status)
        self.username.textChanged.connect(self.reset_connection_status)
        self.password.textChanged.connect(self.reset_connection_status)

        self.layout.addStretch()

    def browse_war_file(self):
        """浏览WAR文件"""
        file, _ = QFileDialog.getOpenFileName(self, "选择kpos.war包", "", "WAR文件 (*.war)")
        if file:
            self.war_path.setText(file)

    def on_test_ssh(self):
        is_valid, error_msg, host, username, password = self._validate_connection_params()
        if not is_valid:
            QMessageBox.warning(self, "参数错误", error_msg)
            return

        self.countdown = 10
        self.ssh_test_finished = False  # 标志位
        self.test_btn.setEnabled(False)
        self.status_label.setText(f"正在测试连接... 剩余{self.countdown}秒")

        def ssh_callback(success, msg):
            if self.ssh_test_finished:
                return
            self.ssh_test_finished = True
            self.timer.stop()
            self.test_btn.setEnabled(True)
            self.status_label.setText(msg)
            if success:
                self.status_label.setStyleSheet("color: green;")
            else:
                self.status_label.setStyleSheet("color: red;")
            self.service.log(f"SSH连接测试结果 - 主机: {host}, 用户: {username}, 结果: {msg}", level="info")

        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: self._update_countdown(ssh_callback))
        self.timer.start(1000)

        self.ssh_thread = SshTestThread(self.service, host, username, password)
        self.ssh_thread.finished_updated.connect(ssh_callback)
        self.ssh_thread.start()

    def _update_countdown(self, callback):
        self.countdown -= 1
        if self.countdown > 0:
            self.status_label.setText(f"正在测试连接... 剩余{self.countdown}秒")
        elif self.countdown == 0:
            self.status_label.setText("连接超时！")
            self.status_label.setStyleSheet("color: red;")
        if self.countdown <= 0 and not self.ssh_test_finished:
            self.ssh_test_finished = True
            self.timer.stop()
            self.test_btn.setEnabled(True)
            callback(False, "连接超时！")

    def reset_connection_status(self):
        self.status_label.setText("连接状态未检测")
        self.status_label.setStyleSheet("color: red;")

    def _show_loading(self, text="校验中..."):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
        from PyQt6.QtGui import QFont, QColor, QPainter, QBrush
        from PyQt6.QtCore import Qt
        class FrostedGlassLabel(QLabel):
            def paintEvent(self, event):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                # 半透明白色背景
                painter.setBrush(QBrush(QColor(255, 255, 255, 180)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(self.rect(), 16, 16)
                super().paintEvent(event)
        self._loading_dialog = QDialog(self)
        self._loading_dialog.setWindowTitle(text)
        self._loading_dialog.setModal(True)
        self._loading_dialog.setWindowFlags(self._loading_dialog.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self._loading_dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout()
        label = FrostedGlassLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        # 使用低饱和度深灰色字体
        label.setStyleSheet("color: #6A6A7A; padding: 18px 24px; letter-spacing: 2px;")
        layout.addWidget(label)
        self._loading_dialog.setLayout(layout)
        self._loading_dialog.setFixedSize(220, 80)
        self._loading_dialog.show()
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

    def _hide_loading(self):
        if hasattr(self, '_loading_dialog') and self._loading_dialog:
            self._loading_dialog.accept()
            self._loading_dialog = None

    def _check_md5_and_confirm(self, host, username, password, local_war_path, remote_war_path="/opt/tomcat7/webapps/kpos.war"):
        """
        检查本地和远程war包MD5是否一致，如一致弹窗提示用户是否继续。
        返回True表示可以继续，False表示用户取消。
        """
        self._show_loading("MD5校验中...")
        try:
            self.log("开始校验本地和远程包MD5一致性...")
            remote_md5 = self._get_remote_md5(host, username, password, remote_war_path)
            local_md5 = self._get_local_md5(local_war_path)
            if remote_md5 and local_md5 and remote_md5 == local_md5:
                self.log(f"本地包和远程包MD5一致: {local_md5}", level="warning")
                reply = QMessageBox.question(
                    self, "疑似相同版本", f"远程包和本地包MD5一致:{remote_md5}，是否继续操作？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return False
            self.log("MD5校验通过，可以继续操作。",level='success')
            return True
        finally:
            self._hide_loading()

    def on_replace_war_linux(self):
        """替换远程WAR包"""

        def replace_war_callback(host, username, password):
            war_path = self.war_path.text()

            # 文件验证
            is_valid, error_msg = self._validate_file_path(war_path, "kpos.war包")
            if not is_valid:
                QMessageBox.warning(self, "提示", error_msg)
                return

            # 新增MD5一致性校验
            if not self._check_md5_and_confirm(host, username, password, war_path):
                return

            # 禁用替换按钮
            self.replace_btn.setEnabled(False)

            # 显示进度条
            if self.parent_window:
                self.parent_window.progress_bar.setVisible(True)
                self.parent_window.progress_bar.setRange(0, 100)
                self.parent_window.progress_bar.setValue(0)
                self.parent_window.progress_bar.setFormat("正在换包：%p%，请勿进行其他操作！")

            self.replace_thread = ReplaceWarThreadLinux(
                self.service, host, username, password, war_path
            )

            # 正确连接信号 - 使用 lambda 包装
            if self.parent_window:
                self.replace_thread.progress_updated.connect(
                    lambda percent: self.parent_window.progress_bar.setValue(percent)
                )
                self.replace_thread.speed_updated.connect(
                    lambda speed: self.parent_window.show_upload_speed(speed)
                )

            self.replace_thread.error_occurred.connect(lambda msg: QMessageBox.warning(self, "错误", msg))
            self.replace_thread.finished_updated.connect(self.on_replace_finished)
            self.replace_thread.start()

        self._execute_with_connection_validation("替换远程WAR包", replace_war_callback)

    def on_replace_finished(self):
        """替换完成后处理"""
        if self.parent_window:
            self.parent_window.progress_bar.setVisible(False)
            self.parent_window.hide_upload_speed()

        if self.replace_btn:
            self.replace_btn.setEnabled(True)

    def on_restart_pos_linux(self):
        """重启Linux POS"""

        def restart_pos_callback(host, username, password):
            # 显示确认弹窗
            reply = QMessageBox.warning(
                self,
                "确认重启",
                "该过程可能耗时1-4分钟，确定重启吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            # 先尝试连接SSH
            try:
                ssh = self.service._connect_ssh(host, username, password)
                ssh.close()
            except Exception as e:
                self.log("SSH连接失败，无法重启POS", level="error")
                return

            # 禁用重启按钮
            self.restart_btn.setEnabled(False)

            # 显示进度条
            if self.parent_window:
                self.parent_window.progress_bar.setVisible(True)
                self.parent_window.progress_bar.setRange(0, 100)
                self.parent_window.progress_bar.setValue(0)
                self.parent_window.progress_bar.setFormat("POS重启中：%p%，请勿进行其他操作！")
            self.restart_thread = RestartPosThreadLinux(self.service, host, username, password)

            # 设置进度条动画更新
            if self.parent_window:
                self.parent_window.setup_progress_animation(600)

            # 在线程完成后更新状态
            self.restart_thread.error_occurred.connect(lambda msg: QMessageBox.warning(self, "错误", msg))
            self.restart_thread.finished_updated.connect(self.on_restart_finished)
            self.restart_thread.start()

        if not self.parent_window:
            QMessageBox.warning(self, "错误", "父窗口未初始化")
            return

        self._execute_with_connection_validation("重启Linux POS", restart_pos_callback)

    def on_restart_finished(self):
        """重启完成后处理"""
        if self.parent_window:
            self.parent_window.on_restart_finished()

        if self.restart_btn:
            self.restart_btn.setEnabled(True)

    def on_restart_tomcat(self):
        """重启Tomcat服务"""

        def restart_tomcat_callback(host, username, password):
            # 禁用重启按钮
            self.restart_tomcat_btn.setEnabled(False)

            # 显示进度条
            if self.parent_window:
                self.parent_window.progress_bar.setVisible(True)
                self.parent_window.progress_bar.setRange(0, 100)
                self.parent_window.progress_bar.setValue(0)
                self.parent_window.progress_bar.setFormat("Tomcat重启中：%p%，请勿进行其他操作！")

            # 启动多线程
            self.restart_tomcat_thread = RestartTomcatThread(self.service, host, username, password)

            # 设置进度条更新
            if self.parent_window:
                self.parent_window.setup_progress_animation(20)

            # 连接信号
            self.restart_tomcat_thread.error_occurred.connect(lambda msg: QMessageBox.warning(self, "错误", msg))
            self.restart_tomcat_thread.finished_updated.connect(self.on_restart_tomcat_finished)
            self.restart_tomcat_thread.start()

        if not self.parent_window:
            QMessageBox.warning(self, "错误", "父窗口未初始化")
            return

        self._execute_with_connection_validation("重启Tomcat服务", restart_tomcat_callback)

    def on_restart_tomcat_finished(self):
        """Tomcat重启完成后处理"""
        if self.parent_window:
            self.parent_window.progress_timer.stop()
            self.parent_window.progress_bar.setValue(100)
            self.parent_window.progress_bar.setVisible(False)

        if self.restart_tomcat_btn:
            self.restart_tomcat_btn.setEnabled(True)

    def on_upgrade_with_package(self):
        """使用升级包升级"""
        if not self.parent_window or not self.war_path:
            QMessageBox.warning(self, "错误", "参数未初始化")
            return
        remote_base_path = "/home/menu"
        try:
            # 检查是否已选择本地升级包路径
            local_package_path = self.war_path.text()
            is_valid, error_msg = self._validate_file_path(local_package_path, "升级包")
            if not is_valid:
                QMessageBox.warning(self, "提示", error_msg)
                return

            # 新增MD5一致性校验（升级包一般是war包，路径同war_path）
            if not self._check_md5_and_confirm(
                self.host_ip.currentText().strip(),
                self.username.text().strip(),
                self.password.text().strip(),
                local_package_path
            ):
                return

            # 禁用按钮
            self.upgrade_package_btn.setEnabled(False)

            # 建立 SSH 连接
            ssh = self.service._connect_ssh(
                self.host_ip.currentText().strip(),
                self.username.text().strip(),
                self.password.text().strip()
            )

            # 扫描远程升级包
            valid_dirs = self.service.scan_upgrade_packages(ssh, remote_base_path)
            if not valid_dirs:
                QMessageBox.warning(self, "提示", "未找到符合条件的升级包！")
                ssh.close()
                self.upgrade_package_btn.setEnabled(True)
                return

            # 弹窗选择升级包
            selected_dir, ok = QInputDialog.getItem(
                self, "选择升级包", "没有心仪的升级包？试试上传升级包功能！", valid_dirs, 0, False
            )

            if not ok or not selected_dir:
                ssh.close()
                self.upgrade_package_btn.setEnabled(True)
                return

            # 显示进度条
            self.parent_window.progress_bar.setVisible(True)
            self.parent_window.progress_bar.setRange(0, 100)
            self.parent_window.progress_bar.setValue(0)
            self.parent_window.progress_bar.setFormat("正在升级：%p%，请勿进行其他操作！")

            # 启动升级线程
            remote_target_path = selected_dir
            self.upgrade_thread = UpgradeThread(
                self.service,
                ssh,
                local_package_path,
                remote_target_path
            )
            self.upgrade_thread.progress_updated.connect(self.parent_window.progress_bar.setValue)
            self.upgrade_thread.error_occurred.connect(lambda msg: QMessageBox.warning(self, "错误", msg))
            self.upgrade_thread.finished_updated.connect(self.on_upgrade_finished)
            self.upgrade_thread.start()
        except Exception as e:
            self.log(f"使用升级包升级过程中出错: {str(e)}", level="error")
            QMessageBox.warning(self, "提示", f"升级过程中出错：{str(e)}")
            if self.upgrade_package_btn:
                self.upgrade_package_btn.setEnabled(True)

    def on_upgrade_finished(self):
        """升级完成后处理"""
        if self.parent_window:
            self.parent_window.progress_bar.setVisible(False)

        if self.upgrade_package_btn:
            self.upgrade_package_btn.setEnabled(True)

    def on_check_remote_md5(self):
        """计算并打印当前志在必得MD5值"""

        def check_remote_md5_callback(host, username, password):
            war_path = "/opt/tomcat7/webapps/kpos.war"
            try:
                ssh = self.service._connect_ssh(host, username, password)
                md5_value = self.service.get_file_md5(ssh, war_path)
                if md5_value:
                    self.service.log(f"{war_path} 的MD5值: {md5_value}", level="info")
                ssh.close()
            except Exception as e:
                self.service.log(f"计算MD5过程中出错: {str(e)}", level="error")

        self._execute_with_connection_validation("查询远程包MD5", check_remote_md5_callback)

    def on_check_local_md5(self):
        """查询本地志在必得MD5值"""
        if not self.war_path:
            QMessageBox.warning(self, "错误", "参数未初始化")
            return

        war_path = self.war_path.text()
        is_valid, error_msg = self._validate_file_path(war_path, "kpos.war包")
        if not is_valid:
            QMessageBox.warning(self, "提示", error_msg)
            return

        try:
            import hashlib
            md5_hash = hashlib.md5()
            with open(war_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
            md5_value = md5_hash.hexdigest()
            self.service.log(f"{war_path} 的MD5值: {md5_value}", level="info")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"计算MD5值时出错：{str(e)}")

    def on_upload_upgrade_package(self):
        """上传升级包"""
        if not self.parent_window:
            QMessageBox.warning(self, "错误", "父窗口未初始化")
            return

        # 选择本地升级包
        file, _ = QFileDialog.getOpenFileName(self, "选择升级包", "", "ZIP文件 (*.zip)")
        if not file:
            return

        def upload_callback(host, username, password):
            self.upload_updater_btn.setEnabled(False)

            # 显示进度条
            self.parent_window.progress_bar.setVisible(True)
            self.parent_window.progress_bar.setRange(0, 100)
            self.parent_window.progress_bar.setValue(0)
            self.parent_window.progress_bar.setFormat("正在上传：%p%，请勿进行其他操作！")

            # 启动上传线程
            self.upload_thread = UploadUpgradePackageThread(
                self.service, host, username, password, file
            )
            self.upload_thread.progress_updated.connect(self.parent_window.progress_bar.setValue)
            self.upload_thread.error_occurred.connect(lambda msg: QMessageBox.warning(self, "错误", msg))
            self.upload_thread.finished_updated.connect(self.on_upload_finished)
            self.upload_thread.start()

        self._execute_with_connection_validation("上传升级包", upload_callback, True, file, "升级包")

    def on_upload_finished(self):
        """上传完成后处理"""
        if self.parent_window:
            self.parent_window.progress_bar.setVisible(False)

        if self.upload_updater_btn:
            self.upload_updater_btn.setEnabled(True)

    def on_download_log(self):
        """日志下载主流程（支持多选，使用完整路径）"""

        def download_log_callback(host, username, password):
            try:
                backend = self.service if hasattr(self.service, '_connect_ssh') else Backend()
                ssh = backend._connect_ssh(host, username, password)
                log_files = backend.scan_remote_logs(ssh)
                if not log_files:
                    QMessageBox.information(self, "无日志文件", "远程目录下未找到日志文件！")
                    ssh.close()
                    return

                # 多选日志文件（展示文件名，返回完整路径）
                dialog = MultiSelectLogDialog(self, log_files)
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    ssh.close()
                    return
                selected_logs = dialog.selected_logs()  # 现在为完整路径
                if not selected_logs:
                    ssh.close()
                    return
                remote_files = selected_logs

                # 选择本地保存目录
                local_dir = QFileDialog.getExistingDirectory(self, "选择本地保存目录")
                if not local_dir:
                    ssh.close()
                    return

                # 批量下载
                local_paths = backend.download_remote_logs(ssh, remote_files, local_dir)
                ssh.close()
                if local_paths:
                    msg = "\n".join([os.path.normpath(p) for p in local_paths])
                    self.service.log(f"日志文件已保存到：\n{msg}", level="success")
                    QMessageBox.information(self, "下载完成", f"日志文件已保存到：\n{msg}")
                else:
                    QMessageBox.warning(self, "下载失败", "未能成功下载任何日志文件！")
            except Exception as e:
                self.service.log(f"下载日志文件过程中出错: {str(e)}", level="error")
                QMessageBox.critical(self, "下载失败", f"下载日志文件失败：{str(e)}")

        self._execute_with_connection_validation("日志下载", download_log_callback)

    def on_backup_data(self):
        """数据备份操作（多线程）"""

        def backup_callback(host, username, password):
            self.backup_failed = False  # 新增标志
            from pos_tool_new.work_threads import BackupThread
            self.backup_thread = BackupThread(self.service, host, username, password)
            self.backup_btn.setEnabled(False)

            if self.parent_window:
                self.parent_window.progress_bar.setVisible(True)
                self.parent_window.progress_bar.setRange(0, 100)
                self.parent_window.progress_bar.setValue(0)
                self.parent_window.progress_bar.setFormat("正在备份数据：%p%，请勿进行其他操作！")

            self.backup_thread.progress_updated.connect(self.parent_window.progress_bar.setValue)
            self.backup_thread.error_occurred.connect(self.on_backup_error)
            self.backup_thread.finished_updated.connect(self.on_backup_finished)  # 修正信号连接
            self.backup_thread.start()

        self._execute_with_connection_validation("数据备份", backup_callback)

    def on_backup_error(self, msg):
        """备份错误处理"""
        self.backup_failed = True
        if self.parent_window:
            self.parent_window.progress_bar.setVisible(False)
        self.backup_btn.setEnabled(True)
        QMessageBox.warning(self, "备份失败", msg)

    def on_backup_finished(self):
        """备份完成处理"""
        if self.parent_window:
            self.parent_window.progress_bar.setVisible(False)
        self.backup_btn.setEnabled(True)
        if not getattr(self, "backup_failed", False):
            QMessageBox.information(self, "备份完成", "数据备份已完成！")

    def on_restore_data(self):
        """数据恢复操作（弹出筛选框，多线程）"""

        def restore_callback(host, username, password):
            # 获取备份项
            items = self.service.list_backup_items(host, username, password)
            if not items:
                QMessageBox.warning(self, "无备份项", "未找到可恢复的数据备份项！")
                return

            # 弹出筛选框
            selected, ok = QInputDialog.getItem(
                self, "选择数据恢复项", "请选择要恢复的数据备份：", items, 0, False
            )
            if not ok or not selected:
                return

            is_zip = selected.endswith('.zip')
            self.restore_btn.setEnabled(False)

            if self.parent_window:
                self.parent_window.progress_bar.setVisible(True)
                self.parent_window.progress_bar.setRange(0, 100)
                self.parent_window.progress_bar.setValue(0)
                self.parent_window.progress_bar.setFormat("正在恢复数据：%p%，请勿进行其他操作！")

            from pos_tool_new.work_threads import RestoreThread
            self.restore_thread = RestoreThread(
                self.service, host, username, password, selected, is_zip
            )
            self.restore_thread.progress_updated.connect(self.parent_window.progress_bar.setValue)
            self.restore_thread.error_occurred.connect(lambda msg: QMessageBox.warning(self, "恢复失败", msg))
            self.restore_thread.finished_updated.connect(self.on_restore_finished)
            self.restore_thread.start()

        self._execute_with_connection_validation("数据恢复", restore_callback)

    def on_restore_finished(self):
        """恢复完成处理"""
        if self.parent_window:
            self.parent_window.progress_bar.setVisible(False)
        self.restore_btn.setEnabled(True)
        QMessageBox.information(self, "恢复完成", "数据恢复已完成！")

    def log(self, message: str, level: str = "info"):
        self.parent_window.append_log(message, level)

    def set_progress_text(self, text):
        if self.parent_window:
            self.parent_window.progress_bar.setFormat(text)

    @pyqtSlot(str)
    def set_speed_text(self, text: str):
        if self.parent_window and hasattr(self.parent_window, 'speed_label'):
            self.parent_window.speed_label.setText(text)
            self.parent_window.speed_label.setVisible(bool(text))

    def _get_remote_md5(self, host, username, password, war_path="/opt/tomcat7/webapps/kpos.war"):
        """获取远程war包MD5值，失败返回None"""
        try:
            ssh = self.service._connect_ssh(host, username, password)
            md5_value = self.service.get_file_md5(ssh, war_path)
            ssh.close()
            self.log(f"正在检查远程MD5值: {md5_value}", level="info")
            return md5_value
        except Exception as e:
            self.service.log(f"远程MD5获取失败: {str(e)}", level="error")
            return None

    def _get_local_md5(self, war_path):
        """获取本地war包MD5值，失败返回None"""
        import hashlib
        try:
            md5_hash = hashlib.md5()
            with open(war_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
            self.log(f"正在检查本地MD5值: {md5_hash.hexdigest()}", level="info")
            return md5_hash.hexdigest()
        except Exception as e:
            self.service.log(f"本地MD5获取失败: {str(e)}", level="error")
            return None

    def on_pipeline_upgrade(self):
        """一键升级流水线：多线程执行替换war包->修改文件->重启pos"""
        # 先比对远程和本地MD5
        host = self.host_ip.currentText().strip()
        username = self.username.text().strip()
        password = self.password.text().strip()
        local_war_path = self.war_path.text() if hasattr(self, 'war_path') else ''
        # 新增MD5一致性校验
        if not self._check_md5_and_confirm(host, username, password, local_war_path):
            return
        reply = QMessageBox.question(
            self, "确认操作", "确定要执行一键升级吗？\n此操作将依次替换远程war包、修改配置并重启POS！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        env = self.get_selected_env(self.env_group)
        from pos_tool_new.work_threads import PipelineUpgradeThread
        self.pipeline_upgrade_btn.setEnabled(False)
        self.parent_window.progress_bar.setVisible(True)
        self.parent_window.progress_bar.setRange(0, 100)
        self.parent_window.progress_bar.setValue(0)
        self.set_progress_text("正在上传/解压war包 ...")
        self.pipeline_thread = PipelineUpgradeThread(self.service, host, username, password, local_war_path, env, self)
        self.pipeline_thread.progress_updated.connect(self.parent_window.progress_bar.setValue)
        self.pipeline_thread.progress_text_updated.connect(self.set_progress_text)  # 线程安全地更新进度文本
        self.pipeline_thread.speed_updated.connect(self.set_speed_text)  # 新增：连接上传速率信号
        self.pipeline_thread.finished_updated.connect(self.on_pipeline_upgrade_finished)
        self.pipeline_thread.start()

    def on_pipeline_upgrade_finished(self, success, msg):
        self.pipeline_upgrade_btn.setEnabled(True)
        self.parent_window.progress_bar.setVisible(False)
        if success:
            QMessageBox.information(self, "升级成功", msg)
        else:
            QMessageBox.critical(self, "升级失败", msg)

    def on_pipeline_package_upgrade(self):
        """一键升级包升级：选择远程升级包目录，将self.war_path指定的war包上传到该目录，执行升级、修改配置、重启POS（全部在子线程完成）"""
        host = self.host_ip.currentText().strip()
        username = self.username.text().strip()
        password = self.password.text().strip()
        env = self.get_selected_env(self.env_group)
        service = self.service
        try:
            # 1. 使用界面指定的war包路径
            war_file = self.war_path.text()
            is_valid, error_msg = self._validate_file_path(war_file, "war包")
            if not is_valid:
                QMessageBox.warning(self, "提示", error_msg)
                return
            # 2.新增MD5一致性校验
            if not self._check_md5_and_confirm(host, username, password, war_file):
                return
            # 3. 扫描远程升级包目录，弹窗选择
            with service._connect_ssh(host, username, password) as ssh:
                remote_dir = "/home/menu"
                upgrade_dirs = service.scan_upgrade_packages(ssh, remote_dir)
            if not upgrade_dirs:
                QMessageBox.warning(self, "提示", "未找到远程升级工具目录！")
                return
            selected_dir, ok = QInputDialog.getItem(self, "选择升级包", "请选择远程升级工具目录：", upgrade_dirs, 0,
                                                    False)
            if not ok or not selected_dir:
                return


            # 确认操作
            reply = QMessageBox.question(
                self, "确认操作", "确定要执行一键升级包升级吗？\n此操作将覆盖远程war包并重启POS！",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            self.pipeline_upgrade_package_btn.setEnabled(False)
            self.parent_window.progress_bar.setVisible(True)
            self.parent_window.progress_bar.setRange(0, 100)
            self.parent_window.progress_bar.setValue(0)
            self.set_progress_text("正在上传war包到升级包目录 ...")
            # 3. 启动升级包升级线程
            from pos_tool_new.work_threads import PipelinePackageUpgradeThread
            self.pipeline_package_thread = PipelinePackageUpgradeThread(
                service, host, username, password, selected_dir, war_file, env, self
            )
            self.pipeline_package_thread.progress_updated.connect(self.parent_window.progress_bar.setValue)
            self.pipeline_package_thread.progress_text_updated.connect(self.set_progress_text)  # 线程安全地更新进度文本
            self.pipeline_package_thread.speed_updated.connect(self.set_speed_text)  # 新增：连接上传速率信号
            self.pipeline_package_thread.finished_updated.connect(self.on_pipeline_package_upgrade_finished)
            self.pipeline_package_thread.start()
        except Exception as e:
            self.log(f"一键升级包升级失败：{str(e)}", level="error")
            QMessageBox.critical(self, "错误", f"一键升级包升级失败：{str(e)}")
            self.pipeline_upgrade_package_btn.setEnabled(True)
            self.parent_window.progress_bar.setVisible(False)

    def on_pipeline_package_upgrade_finished(self, success, msg):
        self.pipeline_upgrade_package_btn.setEnabled(True)
        self.parent_window.progress_bar.setVisible(False)
        if success:
            QMessageBox.information(self, "升级成功", msg)
        else:
            QMessageBox.critical(self, "升级失败", msg)

    def download_war_from_net(self):
        dialog = QInputDialog(self)
        dialog.setWindowTitle("从网络下载WAR包")
        dialog.setLabelText("请输入下载URL：")
        dialog.setTextValue("")
        dialog.setMinimumWidth(700)

        # 获取输入框并设置宽度
        line_edit = dialog.findChild(QLineEdit)
        if line_edit:
            line_edit.setMinimumWidth(650)

        if dialog.exec() and dialog.textValue().strip():
            url = dialog.textValue().strip()
            self.log(f"开始从网络下载: {url}")
            self._start_download_war(url)

    def _start_download_war(self, url):
        import tempfile
        import os
        from pos_tool_new.download_war.download_war_service import DownloadWarService
        from pos_tool_new.work_threads import DownloadWarWorker

        # 进度条逻辑：显示并重置进度条和速度标签
        if hasattr(self, 'parent_window') and self.parent_window:
            self.parent_window.progress_bar.setVisible(True)
            self.parent_window.progress_bar.setValue(0)
            self.parent_window.progress_bar.setFormat("正在下载war...")
            self.parent_window.speed_label.setVisible(True)
            self.parent_window.speed_label.setText("下载速率: 计算中...")
        temp_dir = tempfile.mkdtemp(prefix="war_download_")
        service = DownloadWarService()
        old_cwd = os.getcwd()
        os.chdir(temp_dir)

        self._download_worker = DownloadWarWorker(url, service, expected_size_mb=217)
        self._download_worker.progress_updated.connect(lambda percent: self._handle_download_progress(percent=percent))
        self._download_worker.speed_updated.connect(
            lambda speed: self._handle_download_progress(percent=None, speed=speed))
        self._download_worker.finished_updated.connect(
            lambda success, result: self._handle_download_finished(success, result, temp_dir, old_cwd))
        self._download_worker.start()

    def _handle_download_progress(self, percent, speed=None):
        """处理下载进度更新"""
        # 更新主窗口进度条
        if hasattr(self, 'parent_window') and self.parent_window:
            if percent is not None:
                self.parent_window.progress_bar.setValue(percent)
            if speed:
                self.parent_window.speed_label.setText(f"下载速率: {speed}")

    def _handle_download_finished(self, success, result, temp_dir, old_cwd):
        """处理下载完成"""
        import zipfile
        import os

        os.chdir(old_cwd)

        # 下载结束后隐藏进度条和速度标签
        if hasattr(self, 'parent_window') and self.parent_window:
            self.parent_window.progress_bar.setVisible(False)
            self.parent_window.speed_label.setVisible(False)
            self.parent_window.progress_bar.update()

        if not success:
            QMessageBox.critical(self, "下载失败", result)
            return

        file_path = os.path.join(temp_dir, result)

        # 显示最终完成状态
        if hasattr(self, 'parent_window') and self.parent_window:
            self.parent_window.progress_bar.setValue(100)

        if zipfile.is_zipfile(file_path):
            self.log(f"下载完成！保存为: {file_path} (zip文件)", "success")
            self.log("正在解压文件...")

            # 更新进度显示为解压状态
            if hasattr(self, 'parent_window') and self.parent_window:
                self.parent_window.progress_bar.setVisible(True)
                self.parent_window.progress_bar.setValue(50)
                self.parent_window.progress_bar.setFormat("正在解压war...")
                self.parent_window.speed_label.setText("正在解压文件...")

            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # 查找war文件（兼容大小写）
            war_found = False
            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    self.log(f"解压后发现文件: {f}")
                    if f.lower().endswith('.war'):
                        war_full_path = os.path.join(root, f)
                        self.log(f"找到war文件: {war_full_path}")
                        if self.war_path:
                            self.war_path.setText(war_full_path)
                            self.log("已更新war文件路径到输入框", "success")
                        war_found = True
                        break
                if war_found:
                    break

            if not war_found:
                self.log("未在解压包中找到war文件")
        else:
            self.log(f"解压完成！保存为: {file_path}", "success")
            if self.war_path and file_path.endswith('.war'):
                self.war_path.setText(file_path)

        # 最终完成状态
        if hasattr(self, 'parent_window') and self.parent_window:
            self.parent_window.progress_bar.setValue(100)
            self.parent_window.speed_label.setText("下载完成")
            self.parent_window.progress_bar.setVisible(False)
            self.parent_window.speed_label.setVisible(False)
            self.parent_window.progress_bar.update()

    def on_tail_log_clicked(self):
        # 校验SSH连接参数
        is_valid, error_msg, host, username, password = self._validate_connection_params()
        if not is_valid:
            QMessageBox.warning(self, "参数错误", error_msg)
            return
        try:
            # 连接SSH并获取远程日志列表
            ssh = self.service._connect_ssh(host, username, password)
            log_files = self.service.scan_remote_logs(ssh)
            if not log_files:
                QMessageBox.information(self, "无日志文件", "远程目录下未找到日志文件！")
                ssh.close()
                return
            # 展示文件名，选中后映射回完整路径
            file_names = [os.path.basename(f) for f in log_files]
            selected_idx, ok = QInputDialog.getItem(self, "选择日志文件", "请选择要实时查看的日志文件：", file_names, 0,
                                                    False)
            if not ok or not selected_idx:
                ssh.close()
                return
            # 找到选中的完整路径
            try:
                idx = file_names.index(selected_idx)
                remote_file = log_files[idx]
            except Exception:
                remote_file = selected_idx  # 兜底
            ssh.close()
            # 打开实时日志窗口（远程模式）
            from pos_tool_new.linux_pos.tail_log_window import TailLogWindow
            self.tail_log_window = TailLogWindow(remote_file, ssh_params=(self.service, host, username, password),
                                                 remote=True)
            self.tail_log_window.show()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取远程日志文件失败：{str(e)}")

    def closeEvent(self, event):
        """窗口关闭时安全销毁所有线程"""
        for thread in [self.replace_thread, self.restart_thread, self.restart_tomcat_thread, self.upgrade_thread,
                       self.upload_thread]:
            if thread is not None and thread.isRunning():
                thread.stop()
        event.accept()

    def set_host_ip(self, ip: str):
        """同步设置主机IP到host_ip输入框"""
        if self.host_ip:
            self.host_ip.setCurrentText(ip)

    def on_get_app_version(self):
        """
        查询并打印远程POS应用的版本号
        """

        def get_app_version_callback(host, username, password):
            remote_path = "/opt/menusifu/resources/app/package.json"
            try:
                ssh = self.service._connect_ssh(host, username, password)
                version = self.service.get_app_version(ssh)
                if version:
                    self.service.log(f"POS应用版本: {version}", level="info")
                else:
                    self.service.log(f"未能获取版本号，或文件不存在: {remote_path}", level="warning")
                ssh.close()
            except Exception as e:
                self.service.log(f"获取POS版本号失败: {str(e)}", level="error")

        self._execute_with_connection_validation("查询远程POS版本号", get_app_version_callback)


class MultiSelectLogDialog(QDialog):
    def __init__(self, parent, log_files):
        super().__init__(parent)
        self.setWindowTitle("选择要下载的日志文件（可多选）")
        self.resize(500, 400)
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget(self)
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for log_path in log_files:
            item = QListWidgetItem(os.path.basename(log_path))
            item.setData(256, log_path)
            item.setToolTip(log_path)
            item.setFont(QFont("Consolas", 10))
            self.list_widget.addItem(item)
        # self.list_widget.setStyleSheet("QListWidget { background: #f8f8ff; } QListWidget::item { padding: 6px; } QListWidget::item:selected { background: #cce5ff; color: #003366; }")
        layout.addWidget(self.list_widget)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.setStyleSheet("QDialogButtonBox { padding: 8px; }")
        layout.addWidget(self.button_box)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def selected_logs(self):
        return [item.data(256) for item in self.list_widget.selectedItems()]
