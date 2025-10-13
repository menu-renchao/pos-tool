import os
from typing import Optional, Tuple, Callable

from PyQt6.QtCore import QTimer, pyqtSlot
from PyQt6.QtWidgets import (
    QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QLineEdit, QFileDialog, QGroupBox, QComboBox, QMessageBox,
    QInputDialog, QSizePolicy
)

from pos_tool_new.backend import Backend
from pos_tool_new.linux_pos.linux_service import LinuxService
from pos_tool_new.main import BaseTabWidget, MainWindow
from pos_tool_new.work_threads import ReplaceWarThreadLinux, RestartPosThreadLinux, RestartTomcatThread, UpgradeThread, \
    UploadUpgradePackageThread, SshTestThread


class LinuxTabWidget(BaseTabWidget):
    """Linux选项卡组件"""

    def __init__(self, parent: Optional[MainWindow] = None):
        super().__init__("Linux POS")
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
        self.upload_btn: Optional[QPushButton] = None
        self.upgrade_btn: Optional[QPushButton] = None
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
        # 新建一行布局，包含环境选择和换包升级服务
        top_row_layout = QHBoxLayout()
        # SSH连接设置组
        self.ssh_group = QGroupBox("SSH连接设置")
        ssh_main_layout = QVBoxLayout(self.ssh_group)
        ssh_input_layout = QHBoxLayout()
        host_label = QLabel("主机IP:")
        self.host_ip = QComboBox()
        self.host_ip.addItems([
            "192.168.0.", "192.168.1.", "10.24.1.",
            "10.1.10.", "10.0.10.", "192.168.252.", "192.168.253."
        ])
        self.host_ip.setEditable(True)
        self.host_ip.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        username_label = QLabel("用户名:")
        self.username = QLineEdit("menu")
        password_label = QLabel("密码:")
        self.password = QLineEdit("M2ei#a$19!")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        ssh_input_layout.addWidget(host_label)
        ssh_input_layout.addWidget(self.host_ip)
        ssh_input_layout.addWidget(username_label)
        ssh_input_layout.addWidget(self.username)
        ssh_input_layout.addWidget(password_label)
        ssh_input_layout.addWidget(self.password)
        # 测试连接按钮
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self.on_test_ssh)
        self.test_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        ssh_input_layout.addWidget(self.test_btn)
        self.status_label = QLabel("连接状态未检测")
        self.status_label.setStyleSheet("color: red;")
        self.status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        ssh_input_layout.addWidget(self.status_label)
        # 查询远程包MD5按钮
        self.remote_md5_btn = QPushButton("查询远程包MD5")
        self.remote_md5_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.remote_md5_btn.clicked.connect(self.on_check_remote_md5)
        ssh_input_layout.addWidget(self.remote_md5_btn)
        # 日志下载按钮
        self.download_log_btn = QPushButton("日志下载")
        self.download_log_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.download_log_btn.clicked.connect(self.on_download_log)
        ssh_input_layout.addWidget(self.download_log_btn)
        ssh_main_layout.addLayout(ssh_input_layout)
        self.layout.addWidget(self.ssh_group)

        # 环境选择组（1/3）
        env_group = QGroupBox("配置文件环境选择")
        env_layout = QVBoxLayout(env_group)
        env_btn_layout = QHBoxLayout()
        env_frame, self.env_group = self.create_env_selector("QA")
        env_btn_layout.addWidget(env_frame)
        env_btn_layout.addStretch()
        # 修改文件按钮
        self.modify_btn = QPushButton("修改文件")
        self.modify_btn.clicked.connect(self.on_modify_remote)
        self.modify_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        env_btn_layout.addWidget(self.modify_btn)
        env_layout.addLayout(env_btn_layout)
        top_row_layout.addWidget(env_group, 1)

        # 换包/升级服务组（2/3）
        file_group = QGroupBox("换包/升级服务")
        file_main_layout = QVBoxLayout(file_group)
        file_select_layout = QHBoxLayout()
        self.war_path = QLineEdit()
        self.war_path.setPlaceholderText("请选择war文件路径...")
        btn_browse = QPushButton("选择...")
        btn_browse.clicked.connect(self.browse_war_file)
        btn_download_net = QPushButton("从网络下载")
        btn_download_net.clicked.connect(self.download_war_from_net)
        file_select_layout.addWidget(self.war_path)
        file_select_layout.addWidget(btn_browse)
        file_select_layout.addWidget(btn_download_net)
        file_main_layout.addLayout(file_select_layout)
        file_btn_layout = QHBoxLayout()
        file_btn_layout.addStretch()
        # 查询本地包MD5按钮
        self.local_md5_btn = QPushButton("查询本地包MD5")
        self.local_md5_btn.clicked.connect(self.on_check_local_md5)
        file_btn_layout.addWidget(self.local_md5_btn)
        # 替换远程war包按钮
        self.replace_btn = QPushButton("替换远程war包")
        self.replace_btn.clicked.connect(self.on_replace_war_linux)
        self.replace_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        file_btn_layout.addWidget(self.replace_btn)
        # 上传升级包按钮
        self.upload_btn = QPushButton("上传升级包")
        self.upload_btn.clicked.connect(self.on_upload_upgrade_package)
        self.upload_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        file_btn_layout.addWidget(self.upload_btn)

        # 为上传按钮添加帮助按钮
        self.add_help_button(self.upload_btn, "此功能会将zip升级包上传到「/home/menu」下并解压。")

        # 使用升级包升级按钮
        self.upgrade_btn = QPushButton("使用升级包升级")
        self.upgrade_btn.clicked.connect(self.on_upgrade_with_package)
        self.upgrade_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        file_btn_layout.addWidget(self.upgrade_btn)

        # 为升级按钮添加帮助按钮
        self.add_help_button(
            self.upgrade_btn,
            "此功能会扫描「/home/menu」下的所有升级工具。\n"
            "如果未发现您需要的升级工具，请使用【上传升级包】功能。"
        )
        top_row_layout.addWidget(file_group, 2)
        file_main_layout.addLayout(file_btn_layout)
        self.layout.addLayout(top_row_layout)


        # 操作按钮组
        action_group = QGroupBox("重启/数据服务")
        action_layout = QHBoxLayout(action_group)
        action_layout.addStretch()
        self.restart_tomcat_btn = QPushButton("重启Tomcat")
        self.restart_tomcat_btn.clicked.connect(self.on_restart_tomcat)
        action_layout.addWidget(self.restart_tomcat_btn)
        self.restart_btn = QPushButton("重启pos")
        self.restart_btn.clicked.connect(self.on_restart_pos_linux)
        action_layout.addWidget(self.restart_btn)
        self.backup_btn = QPushButton("数据备份")
        self.backup_btn.clicked.connect(self.on_backup_data)
        action_layout.addWidget(self.backup_btn)
        self.restore_btn = QPushButton("数据恢复")
        self.restore_btn.clicked.connect(self.on_restore_data)
        action_layout.addWidget(self.restore_btn)

        # 新增流水线布局和一键升级按钮
        pipeline_group = QGroupBox("流水线")
        pipeline_layout = QHBoxLayout(pipeline_group)
        pipeline_layout.addStretch()  # 左侧留白，按钮靠右
        self.upgrade_btn = QPushButton("一键升级")
        self.add_help_button(self.upgrade_btn, "依次执行【替换远程war包】->【修改文件】->【重启pos】")
        self.upgrade_btn.clicked.connect(self.on_pipeline_upgrade)
        pipeline_layout.addWidget(self.upgrade_btn)
        self.upgrade_package_btn = QPushButton("一键升级包升级")
        self.add_help_button(self.upgrade_package_btn, "依次执行【使用升级包升级】->【修改文件】->【重启pos】")
        self.upgrade_package_btn.clicked.connect(self.on_pipeline_package_upgrade)
        pipeline_layout.addWidget(self.upgrade_package_btn)
        self.layout.addLayout(pipeline_layout)

        # 新建一行布局，包含 action_group 和 pipeline_group，水平平分
        action_pipeline_layout = QHBoxLayout()
        action_pipeline_layout.addWidget(action_group)
        action_pipeline_layout.addWidget(pipeline_group)
        action_pipeline_layout.setStretch(0, 1)  # action_group 占一份
        action_pipeline_layout.setStretch(1, 1)  # pipeline_group 占一份
        self.layout.addLayout(action_pipeline_layout)

        self.layout.addStretch()
        self.host_ip.currentTextChanged.connect(self.reset_connection_status)
        self.username.textChanged.connect(self.reset_connection_status)
        self.password.textChanged.connect(self.reset_connection_status)

    def browse_war_file(self):
        """浏览WAR文件"""
        file, _ = QFileDialog.getOpenFileName(self, "选择kpos.war包", "", "WAR文件 (*.war)")
        if file:
            self.war_path.setText(file)

    def show_upgrade_help(self, info: str):
        """显示升级帮助"""
        QMessageBox.information(
            self,
            "使用说明",
            info
        )

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
        self.ssh_thread.finished.connect(ssh_callback)
        self.ssh_thread.start()

    def _update_countdown(self, callback):
        self.countdown -= 1
        if self.countdown > 0:
            self.status_label.setText(f"正在测试连接... 剩余{self.countdown}秒")
        elif self.countdown == 0:
            self.status_label.setText("连接超时！")
        if self.countdown <= 0 and not self.ssh_test_finished:
            self.ssh_test_finished = True
            self.timer.stop()
            self.test_btn.setEnabled(True)
            callback(False, "连接超时！")

    def reset_connection_status(self):
        self.status_label.setText("连接状态未检测")
        self.status_label.setStyleSheet("color: red;")

    def on_modify_remote(self):
        """修改远程文件"""

        def modify_remote_callback(host, username, password):
            if not self.env_group:
                QMessageBox.warning(self, "错误", "环境选择器未初始化")
                return

            env = self.get_selected_env(self.env_group)
            self.log(f"开始修改远程文件 - 主机: {host}, 用户: {username}, 环境: {env}")
            self.service.modify_remote_files(host, username, password, env)

        self._execute_with_connection_validation("修改远程文件", modify_remote_callback)

    def on_replace_war_linux(self):
        """替换远程WAR包"""

        def replace_war_callback(host, username, password):
            war_path = self.war_path.text()

            # 文件验证
            is_valid, error_msg = self._validate_file_path(war_path, "kpos.war包")
            if not is_valid:
                QMessageBox.warning(self, "提示", error_msg)
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
            self.replace_thread.finished.connect(self.on_replace_finished)
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
            self.restart_thread.finished.connect(self.on_restart_finished)
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
            self.restart_tomcat_thread.finished.connect(self.on_restart_tomcat_finished)
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

            # 禁用按钮
            self.upgrade_btn.setEnabled(False)

            # 建立 SSH 连接
            ssh = self.service._connect_ssh(
                self.host_ip.currentText(),
                self.username.text(),
                self.password.text()
            )

            # 扫描远程升级包
            valid_dirs = self.service.scan_upgrade_packages(ssh, remote_base_path)
            if not valid_dirs:
                QMessageBox.warning(self, "提示", "未找到符合条件的升级包！")
                ssh.close()
                self.upgrade_btn.setEnabled(True)
                return

            # 弹窗选择升级包
            selected_dir, ok = QInputDialog.getItem(
                self, "选择升级包", "没有心仪的升级包？试试上传升级包功能！", valid_dirs, 0, False
            )

            if not ok or not selected_dir:
                ssh.close()
                self.upgrade_btn.setEnabled(True)
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
            self.upgrade_thread.finished.connect(self.on_upgrade_finished)
            self.upgrade_thread.start()
        except Exception as e:
            self.log(f"使用升级包升级过程中出错: {str(e)}", level="error")
            QMessageBox.warning(self, "提示", f"升级过程中出错：{str(e)}")
            if self.upgrade_btn:
                self.upgrade_btn.setEnabled(True)

    def on_upgrade_finished(self):
        """升级完成后处理"""
        if self.parent_window:
            self.parent_window.progress_bar.setVisible(False)

        if self.upgrade_btn:
            self.upgrade_btn.setEnabled(True)

    def on_check_remote_md5(self):
        """计算并打印当前包的MD5值"""

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
        """查询本地包的MD5值"""
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
            self.upload_btn.setEnabled(False)

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
            self.upload_thread.finished.connect(self.on_upload_finished)
            self.upload_thread.start()

        self._execute_with_connection_validation("上传升级包", upload_callback, True, file, "升级包")

    def on_upload_finished(self):
        """上传完成后处理"""
        if self.parent_window:
            self.parent_window.progress_bar.setVisible(False)

        if self.upload_btn:
            self.upload_btn.setEnabled(True)

    def on_download_log(self):
        """日志下载主流程"""

        def download_log_callback(host, username, password):
            try:
                backend = self.service if hasattr(self.service, '_connect_ssh') else Backend()
                ssh = backend._connect_ssh(host, username, password)
                log_files = backend.scan_remote_logs(ssh)
                if not log_files:
                    QMessageBox.information(self, "无日志文件", "远程目录下未找到日志文件！")
                    ssh.close()
                    return

                # 选择日志文件
                file, ok = QInputDialog.getItem(self, "选择日志文件", "请选择要下载的日志文件：", log_files, 0, False)
                if not ok or not file:
                    ssh.close()
                    return

                remote_file = f"/opt/tomcat7/logs/{file}"

                # 选择本地保存目录
                local_dir = QFileDialog.getExistingDirectory(self, "选择本地保存目录")
                if not local_dir:
                    ssh.close()
                    return

                # 下载文件
                local_path = backend.download_remote_log(ssh, remote_file, local_dir)
                ssh.close()
                local_path = os.path.normpath(local_path)
                self.service.log(f"日志文件已保存到：{local_path}", level="success")
                QMessageBox.information(self, "下载完成", f"日志文件已保存到：\n{local_path}")

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
            self.backup_thread.finished.connect(self.on_backup_finished)  # 修正信号连接
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
            self.restore_thread.finished.connect(self.on_restore_finished)
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

    def on_pipeline_upgrade(self):
        """一键升级流水线：多线程执行替换war包->修改文件->重启pos"""
        reply = QMessageBox.question(
            self, "确认操作", "确定要执行一键升级吗？\n此操作将依次替换远程war包、修改配置并重启POS！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        host = self.host_ip.currentText()
        username = self.username.text()
        password = self.password.text()
        local_war_path = self.war_path.text() if hasattr(self, 'war_path') else ''
        env = self.get_selected_env(self.env_group)
        from pos_tool_new.work_threads import PipelineUpgradeThread
        self.upgrade_btn.setEnabled(False)
        self.parent_window.progress_bar.setVisible(True)
        self.parent_window.progress_bar.setRange(0, 100)
        self.parent_window.progress_bar.setValue(0)
        self.set_progress_text("正在上传/解压war包 ...")
        self.pipeline_thread = PipelineUpgradeThread(self.service, host, username, password, local_war_path, env, self)
        self.pipeline_thread.progress_updated.connect(self.parent_window.progress_bar.setValue)
        self.pipeline_thread.progress_text_updated.connect(self.set_progress_text)  # 线程安全地更新进度文本
        self.pipeline_thread.speed_updated.connect(self.set_speed_text)  # 新增：连接上传速率信号
        self.pipeline_thread.finished.connect(self.on_pipeline_upgrade_finished)
        self.pipeline_thread.start()

    def on_pipeline_upgrade_finished(self, success, msg):
        self.upgrade_btn.setEnabled(True)
        self.parent_window.progress_bar.setVisible(False)
        if success:
            QMessageBox.information(self, "升级成功", msg)
        else:
            QMessageBox.critical(self, "升级失败", msg)

    def on_pipeline_package_upgrade(self):
        """一键升级包升级：选择远程升级包目录，将self.war_path指定的war包上传到该目录，执行升级、修改配置、重启POS（全部在子线程完成）"""
        host = self.host_ip.currentText()
        username = self.username.text()
        password = self.password.text()
        env = self.get_selected_env(self.env_group)
        service = self.service
        try:
            # 1. 扫描远程升级包目录，弹窗选择
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
            # 2. 使用界面指定的war包路径
            war_file = self.war_path.text()
            is_valid, error_msg = self._validate_file_path(war_file, "war包")
            if not is_valid:
                QMessageBox.warning(self, "提示", error_msg)
                return

            # 确认操作
            reply = QMessageBox.question(
                self, "确认操作", "确定要执行一键升级包升级吗？\n此操作将覆盖远程war包并重启POS！",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            self.upgrade_package_btn.setEnabled(False)
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
            self.pipeline_package_thread.finished.connect(self.on_pipeline_package_upgrade_finished)
            self.pipeline_package_thread.start()
        except Exception as e:
            self.log(f"一键升级包升级失败：{str(e)}", level="error")
            QMessageBox.critical(self, "错误", f"一键升级包升级失败：{str(e)}")
            self.upgrade_package_btn.setEnabled(True)
            self.parent_window.progress_bar.setVisible(False)

    def on_pipeline_package_upgrade_finished(self, success, msg):
        self.upgrade_package_btn.setEnabled(True)
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
            self.parent_window.speed_label.clear()

        self.log("正在下载，请稍候...")
        temp_dir = tempfile.mkdtemp(prefix="war_download_")
        service = DownloadWarService()
        old_cwd = os.getcwd()
        os.chdir(temp_dir)

        self._download_worker = DownloadWarWorker(url, service, expected_size_mb=217)
        self._download_worker.progress_updated.connect(lambda percent: self._handle_download_progress(percent=percent))
        self._download_worker.speed_updated.connect(
            lambda speed: self._handle_download_progress(percent=None, speed=speed))
        self._download_worker.finished.connect(
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
            self.log(f"下载完成！保存为: {file_path}", "success")
            if self.war_path and file_path.endswith('.war'):
                self.war_path.setText(file_path)

        # 最终完成状态
        if hasattr(self, 'parent_window') and self.parent_window:
            self.parent_window.progress_bar.setValue(100)
            self.parent_window.speed_label.setText("下载完成")
            self.parent_window.progress_bar.setVisible(False)
            self.parent_window.speed_label.setVisible(False)
            self.parent_window.progress_bar.update()
