import os
import zipfile
from PyQt6.QtWidgets import (
    QPushButton, QHBoxLayout, QLineEdit, QFileDialog, QGroupBox, QMessageBox, QInputDialog, QSizePolicy
)
from pos_tool_new.main import BaseTabWidget
from pos_tool_new.windows_pos.windows_service import WindowsService
from pos_tool_new.work_threads import RestartPosThreadWindows, ReplaceWarThreadWindows, DownloadWarWorker
from pos_tool_new.download_war.download_war_service import DownloadWarService


class WindowsTabWidget(BaseTabWidget):
    def __init__(self, parent=None):
        super().__init__("Windows POS")
        self.parent_window = parent
        self.service = WindowsService()
        self._download_handled = False
        self._current_thread = None  # 用于管理后台线程
        self.setup_ui()

    def setup_ui(self):
        self._setup_env_selector()
        self._setup_path_selector()
        self._setup_war_selector()
        self._setup_buttons()
        self.layout.addStretch()

    def _setup_env_selector(self):
        env_group = QGroupBox("配置文件环境选择")
        env_layout = QHBoxLayout(env_group)
        env_frame, self.env_group = self.create_env_selector("QA")
        env_layout.addWidget(env_frame)
        self.layout.addWidget(env_group)

    def _setup_path_selector(self):
        path_group = QGroupBox("基础目录")
        path_layout = QHBoxLayout(path_group)
        self.base_path = QLineEdit(r"C:\Wisdomount\Menusifu\application")
        self.base_path.setPlaceholderText("请选择基础目录...")
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self.browse_directory)
        path_layout.addWidget(self.base_path)
        path_layout.addWidget(btn_browse)
        self.layout.addWidget(path_group)

    def _setup_war_selector(self):
        upload_group = QGroupBox("选择kpos.war包")
        upload_layout = QHBoxLayout(upload_group)
        self.war_path = QLineEdit()
        self.war_path.setPlaceholderText("请选择war文件路径...")
        btn_upload = QPushButton("选择...")
        btn_upload.clicked.connect(self.upload_war_file)
        self.btn_download_net = QPushButton("从网络下载WAR包")
        self.btn_download_net.clicked.connect(self.download_war_from_net)
        upload_layout.addWidget(self.war_path)
        upload_layout.addWidget(btn_upload)
        upload_layout.addWidget(self.btn_download_net)
        self.layout.addWidget(upload_group)

    def _setup_buttons(self):
        btn_group = QGroupBox()
        btn_layout = QHBoxLayout(btn_group)
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
        self.layout.addWidget(btn_group)

    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择基础目录", self.base_path.text())
        if dir_path:
            self.base_path.setText(dir_path)

    def upload_war_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择kpos.war包", "", "WAR文件 (*.war)")
        if file:
            self.war_path.setText(file)

    def on_scan_local(self):
        self.service.scan_local(self.base_path.text(), self.get_selected_env(self.env_group))

    def on_modify_local(self):
        self.service.modify_local_files(self.base_path.text(), self.get_selected_env(self.env_group))

    def on_restart_pos_windows(self):
        versions = self._get_versions()
        if not versions:
            return
        selected_version = self.select_version(versions)
        if selected_version:
            self._start_thread(RestartPosThreadWindows, selected_version)

    def on_replace_war_windows(self):
        try:
            war_path = self.war_path.text()
            if not war_path or not os.path.isfile(war_path):
                QMessageBox.warning(self, "提示", "请先选择本地 kpos.war 包文件！")
                return
            base_dir = self.base_path.text()
            if not base_dir or not os.path.isdir(base_dir):
                QMessageBox.warning(self, "提示", "基础目录无效或不存在！")
                return
            versions = self._get_versions()
            if not versions:
                QMessageBox.warning(self, "提示", "未找到任何版本目录！")
                return
            selected_version = self.select_version(versions)
            if selected_version:
                try:
                    self._start_thread(ReplaceWarThreadWindows, selected_version, war_path)
                except Exception as e:
                    QMessageBox.critical(self, "线程启动失败", f"启动替换线程失败：{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "操作异常", f"换包操作异常：{str(e)}")

    def _get_versions(self):
        try:
            return [d for d in os.listdir(self.base_path.text()) if os.path.isdir(os.path.join(self.base_path.text(), d))]
        except Exception as e:
            QMessageBox.warning(self, "提示", f"读取目录失败：{str(e)}")
            return []

    def _start_thread(self, thread_class, *args):
        if self._current_thread is not None and self._current_thread.isRunning():
            QMessageBox.warning(self, "警告", "有线程正在运行，请等待其结束。")
            return
        thread = thread_class(self.service, self.base_path.text(), *args)
        thread.error_occurred.connect(lambda msg: QMessageBox.warning(self, "错误", msg))
        thread.finished.connect(self._clear_current_thread)
        self._current_thread = thread
        thread.start()

    def _clear_current_thread(self):
        self._current_thread = None

    def closeEvent(self, event):
        if self._current_thread is not None and self._current_thread.isRunning():
            self._current_thread.quit()
            self._current_thread.wait()
        event.accept()

    def select_version(self, versions):
        if len(versions) == 1:
            return versions[0]
        selected_version, ok = QInputDialog.getItem(self, "选择版本", "请选择版本：", versions, 0, False)
        return selected_version if ok else None

    def download_war_from_net(self):
        url = self._get_download_url()
        if url:
            self.service.log(f"开始从网络下载: {url}")
            self._download_war_from_net(url)

    def _get_download_url(self):
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
            return dialog.textValue().strip()
        return None

    def _download_war_from_net(self, url):
        import tempfile
        self._download_handled = False
        self.btn_download_net.setEnabled(False)
        self._show_progress_bar()
        temp_dir = tempfile.mkdtemp(prefix="war_download_")
        os.chdir(temp_dir)
        self._download_worker = DownloadWarWorker(url, DownloadWarService(), expected_size_mb=217)
        self._download_worker.progress_updated.connect(self._handle_download_progress)
        self._download_worker.finished.connect(
            lambda success, result: self._handle_download_finished(success, result, temp_dir, os.getcwd()))
        self._download_worker.start()

    def _show_progress_bar(self):
        if hasattr(self.parent_window, 'progress_bar') and hasattr(self.parent_window, 'speed_label'):
            self.parent_window.progress_bar.setVisible(True)
            self.parent_window.progress_bar.setValue(0)
            self.parent_window.progress_bar.setFormat("正在下载war...")
            self.parent_window.speed_label.setVisible(True)
            self.parent_window.speed_label.clear()

    def _handle_download_progress(self, percent, speed=None, downloaded=None, total=None):
        if hasattr(self.parent_window, 'progress_bar'):
            self.parent_window.progress_bar.setValue(percent)
            if speed and hasattr(self.parent_window, 'speed_label'):
                self.parent_window.speed_label.setText(f"下载速度: {speed}")

    def _handle_download_finished(self, success, result, temp_dir, old_cwd):
        if self._download_handled:
            return
        self._download_handled = True
        os.chdir(old_cwd)
        self.btn_download_net.setEnabled(True)
        self._hide_progress_bar()
        if not success:
            self.service.log(f"下载失败: {result}", "error")
            return
        self._process_downloaded_file(result, temp_dir)

    def _hide_progress_bar(self):
        if hasattr(self.parent_window, 'progress_bar'):
            self.parent_window.progress_bar.setVisible(False)
        if hasattr(self.parent_window, 'speed_label'):
            self.parent_window.speed_label.setVisible(False)

    def _process_downloaded_file(self, result, temp_dir):
        file_path = os.path.join(temp_dir, result) if not os.path.isabs(result) else result
        if file_path.lower().endswith('.zip'):
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
            except Exception as e:
                self.service.log(f"解压失败: {str(e)}", "error")
                return
        self._find_and_set_war_path(temp_dir)

    def _find_and_set_war_path(self, temp_dir):
        war_path = ""
        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.lower() == "kpos.war":
                    war_path = os.path.abspath(os.path.join(root, file))
                    break
            if war_path:
                break
        if war_path:
            self.war_path.setText(war_path)
            self.service.log(f"kpos.war 路径已自动填充：\n{war_path}", "success")
        else:
            self.service.log("下载并解压后未找到kpos.war文件，请手动选择。", "warning")