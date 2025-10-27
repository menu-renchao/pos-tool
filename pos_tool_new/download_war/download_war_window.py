import os

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox

from pos_tool_new.main import BaseTabWidget, MainWindow
from .download_war_service import DownloadWarService


class DownloadWarTabWidget(BaseTabWidget):
    def __init__(self, parent=None):
        super().__init__("Download War", parent)
        self.download_btn = None
        self.url_input = None
        self.parent_window: MainWindow = parent
        self.service = DownloadWarService()
        self.worker = None
        self.init_ui()

    def init_ui(self):
        layout = self.layout
        url_layout = QHBoxLayout()
        url_label = QLabel('下载URL:')
        self.url_input = QLineEdit()
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)
        button_layout = QHBoxLayout()
        self.download_btn = QPushButton('开始下载')
        self.download_btn.setMaximumWidth(120)  # 设置最大宽度，防止按钮过长
        self.download_btn.clicked.connect(self.start_download)
        self.cancel_btn = QPushButton('取消下载')
        self.cancel_btn.setMaximumWidth(120)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_download)
        button_layout.addStretch()  # 左侧留空，使按钮靠右
        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()  # 右侧留空，按钮居中或靠右
        layout.addLayout(button_layout)

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, '警告', '请输入下载URL')
            return

        # 重置进度条
        if self.parent_window:
            self.parent_window.progress_bar.setVisible(True)
            self.parent_window.progress_bar.setValue(0)
            self.parent_window.progress_bar.setFormat("正在下载war...")
            self.parent_window.speed_label.setVisible(True)
            self.parent_window.speed_label.setText("下载速率: 计算中...")

        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.service.log("开始下载任务...")

        from pos_tool_new.work_threads import DownloadWarWorker
        self.worker = DownloadWarWorker(url, self.service, expected_size_mb=217)
        self.worker.progress_updated.connect(self.log_progress)
        self.worker.speed_updated.connect(self.log_speed)  # 新增速率信号连接
        self.worker.finished_updated.connect(self.download_finished)
        self.worker.start()

    def cancel_download(self):
        if self.worker:
            self.worker.cancel()
            self.cancel_btn.setEnabled(False)
            self.service.log("用户请求取消下载...", "warning")

    def log_progress(self, percent, speed=None, downloaded=None, total=None):
        # 更新主窗口进度条
        if self.parent_window:
            self.parent_window.progress_bar.setValue(percent)
            # 进度条文本可显示详细进度
            if downloaded is not None and total is not None:
                self.parent_window.progress_bar.setFormat("正在下载war...")
            if speed:
                self.parent_window.speed_label.setText(f"下载速率: {speed}")

    def log_speed(self, speed):
        if self.parent_window:
            self.parent_window.speed_label.setText(f"下载速率: {speed}")

    def download_finished(self, success, message):
        # 重置UI状态
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        if self.parent_window:
            self.parent_window.progress_bar.setVisible(False)
            self.parent_window.speed_label.setVisible(False)
            self.parent_window.progress_bar.update()

        if success:
            abs_path = os.path.abspath(message)
            self.service.log(f"下载成功! 文件保存为: {abs_path}", "success")
            QMessageBox.information(self, '成功', f'文件已保存为: {abs_path}')
        else:
            self.service.log(f"下载失败: {message}", "error")
            QMessageBox.critical(self, '失败', message)
