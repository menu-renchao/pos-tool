import os
from typing import List, Optional

from PyQt6.QtWidgets import (
    QPushButton, QHBoxLayout, QLineEdit, QFileDialog, QGroupBox, QMessageBox, QInputDialog, QSizePolicy
)

from pos_tool_new.main import BaseTabWidget
from pos_tool_new.windows_pos.windows_service import WindowsService
from pos_tool_new.work_threads import RestartPosThreadWindows, ReplaceWarThreadWindows


class WindowsTabWidget(BaseTabWidget):
    """Windows选项卡组件"""

    def __init__(self, parent=None):
        super().__init__("Windows POS")
        self.parent_window = parent
        self.service = WindowsService()
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        # 配置文件环境选择
        env_group = QGroupBox("配置文件环境选择")
        env_layout = QHBoxLayout(env_group)
        env_frame, self.env_group = self.create_env_selector("QA")
        env_layout.addWidget(env_frame)
        self.layout.addWidget(env_group)

        # 路径选择
        path_group = QGroupBox("基础目录")
        path_layout = QHBoxLayout(path_group)
        self.base_path = QLineEdit(r"C:\Wisdomount\Menusifu\application")
        self.base_path.setPlaceholderText("请选择基础目录...")
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self.browse_directory)
        path_layout.addWidget(self.base_path)
        path_layout.addWidget(btn_browse)
        self.layout.addWidget(path_group)

        # 选择WAR文件
        upload_group = QGroupBox("选择kpos.war包")
        upload_layout = QHBoxLayout(upload_group)
        self.war_path = QLineEdit()
        self.war_path.setPlaceholderText("请选择war文件路径...")
        btn_upload = QPushButton("选择...")
        btn_upload.clicked.connect(self.upload_war_file)
        upload_layout.addWidget(self.war_path)
        upload_layout.addWidget(btn_upload)
        # 从网络下载WAR包按钮
        btn_download_net = QPushButton("从网络下载WAR包")
        btn_download_net.clicked.connect(self.download_war_from_net)
        upload_layout.addWidget(btn_download_net)
        self.layout.addWidget(upload_group)

        # 按钮区域
        self.create_button_layout()
        self.layout.addStretch()

    def create_button_layout(self):
        """创建按钮布局，并新增从网络下载WAR包按钮"""
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(2)

        buttons = [
            ("扫描目录", self.on_scan_local),
            ("修改文件", self.on_modify_local),
            ("替换本地war包", self.on_replace_war_windows),
            ("重启pos", self.on_restart_pos_windows)
        ]

        for text, slot in buttons:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)

    def browse_directory(self):
        """浏览目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择基础目录", self.base_path.text())
        if dir_path:
            self.base_path.setText(dir_path)

    def upload_war_file(self):
        """上传WAR文件"""
        file, _ = QFileDialog.getOpenFileName(self, "选择kpos.war包", "", "WAR文件 (*.war)")
        if file:
            self.war_path.setText(file)

    def on_scan_local(self):
        self.service.scan_local(
            self.base_path.text(),
            self.get_selected_env(self.env_group)
        )

    def on_modify_local(self):
        """修改本地文件"""
        self.service.modify_local_files(
            self.base_path.text(),
            self.get_selected_env(self.env_group)
        )

    def on_restart_pos_windows(self):
        base_path = self.base_path.text()
        try:
            versions = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
        except Exception as e:
            QMessageBox.warning(self, "提示", f"读取目录失败：{str(e)}")
            return

        if not versions:
            QMessageBox.warning(self, "提示", "未找到任何版本目录！")
            return

        selected_version = self.select_version(versions)
        if not selected_version:
            return

        self.restart_thread = RestartPosThreadWindows(
            self.service,
            base_path,
            selected_version
        )
        self.restart_thread.error_occurred.connect(lambda msg: QMessageBox.warning(self, "错误", msg))
        self.restart_thread.start()

    def on_replace_war_windows(self):
        war_path = self.war_path.text()
        if not war_path:
            QMessageBox.warning(self, "提示", "请先选择本地 kpos.war 包文件！")
            return

        base_path = self.base_path.text()
        try:
            versions = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
        except Exception as e:
            QMessageBox.warning(self, "提示", f"读取目录失败：{str(e)}")
            return

        if not versions:
            QMessageBox.warning(self, "提示", "未找到任何版本目录！")
            return

        selected_version = self.select_version(versions)
        if not selected_version:
            return

        self.replace_thread = ReplaceWarThreadWindows(
            self.service,
            base_path,
            selected_version,
            war_path
        )
        self.replace_thread.error_occurred.connect(lambda msg: QMessageBox.warning(self, "错误", msg))
        self.replace_thread.start()

    def select_version(self, versions: List[str]) -> Optional[str]:
        """选择版本"""
        if len(versions) == 1:
            return versions[0]

        selected_version, ok = QInputDialog.getItem(
            self, "选择版本", "请选择版本：", versions, 0, False
        )
        return selected_version if ok else None

    def download_war_from_net(self):
        dialog = QInputDialog(self)
        dialog.setWindowTitle("从网络下载WAR包")
        dialog.setLabelText("请输入下载URL：")
        dialog.setTextValue("")
        dialog.setMinimumWidth(700)
        line_edit = dialog.findChild(QLineEdit)
        if line_edit:
            line_edit.setMinimumWidth(650)
        if dialog.exec() and dialog.textValue().strip():
            url = dialog.textValue().strip()
            if self.parent_window and hasattr(self.parent_window, 'append_log'):
                self.service.log(f"开始从网络下载: {url}")
            self._download_war_from_net(url)

    def _download_war_from_net(self, url):
        import tempfile
        import os
        from pos_tool_new.download_war.download_war_service import DownloadWarService
        from pos_tool_new.work_threads import DownloadWarWorker
        if self.parent_window and hasattr(self.parent_window, 'progress_bar') and hasattr(self.parent_window,
                                                                                          'speed_label'):
            self.parent_window.progress_bar.setVisible(True)
            self.parent_window.progress_bar.setValue(0)
            self.parent_window.progress_bar.setFormat("正在下载war...")
            self.parent_window.speed_label.setVisible(True)
            self.parent_window.speed_label.clear()
        if self.parent_window and hasattr(self.parent_window, 'append_log'):
            self.service.log("正在下载，请稍候...")
        temp_dir = tempfile.mkdtemp(prefix="war_download_")
        service = DownloadWarService()
        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        self._download_worker = DownloadWarWorker(url, service, expected_size_mb=217)
        self._download_worker.progress_updated.connect(self._handle_download_progress)
        self._download_worker.finished.connect(
            lambda success, result: self._handle_download_finished(success, result, temp_dir, old_cwd))
        self._download_worker.start()

    def _handle_download_progress(self, percent, speed=None, downloaded=None, total=None):
        if self.parent_window and hasattr(self.parent_window, 'progress_bar'):
            self.parent_window.progress_bar.setValue(percent)
            if speed and hasattr(self.parent_window, 'speed_label'):
                self.parent_window.speed_label.setText(f"下载速度: {speed}")

    def _handle_download_finished(self, success, result, temp_dir, old_cwd):
        import os
        os.chdir(old_cwd)
        if self.parent_window and hasattr(self.parent_window, 'progress_bar'):
            self.parent_window.progress_bar.setVisible(False)
        if self.parent_window and hasattr(self.parent_window, 'speed_label'):
            self.parent_window.speed_label.setVisible(False)
