import os
import threading
import time

from PyQt6.QtCore import QThread, pyqtSignal, QObject

from pos_tool_new.backend import Backend
from pos_tool_new.download_war.download_war_service import DownloadWarService


class BaseWorkerThread(QThread):
    """基础工作线程类，提供通用的错误处理功能"""
    error_signal = pyqtSignal(str)
    finished = pyqtSignal()  # 添加finished信号

    def __init__(self):
        super().__init__()
        self._is_running = True

    def run(self):
        try:
            self._run_impl()
        except Exception as e:
            self.error_signal.emit(f"线程执行失败: {str(e)}")
        finally:
            self.finished.emit()  # 确保总是发出finished信号

    def _run_impl(self):
        """子类需要实现的具体运行逻辑"""
        raise NotImplementedError("子类必须实现 _run_impl 方法")

    def run_with_error_handling(self, func, *args, **kwargs):
        """执行函数并捕获异常"""
        try:
            func(*args, **kwargs)
        except Exception as e:
            self.error_signal.emit(f"操作失败: {str(e)}")


class RestartPosThreadLinux(BaseWorkerThread):
    def __init__(self, backend: Backend, host: str, username: str, password: str):
        super().__init__()
        self.backend = backend
        self.host = host
        self.username = username
        self.password = password

    def run(self):
        self.run_with_error_handling(
            self.backend.restart_pos_linux,
            self.host, self.username, self.password
        )
        self.finished.emit()


class ReplaceWarThreadLinux(BaseWorkerThread):
    progress_signal = pyqtSignal(int)
    speed_signal = pyqtSignal(str)  # 修改为str类型

    def __init__(self, backend: Backend, host: str, username: str, password: str, war_path: str):
        super().__init__()
        self.backend = backend
        self.host = host
        self.username = username
        self.password = password
        self.war_path = war_path

    def run(self):
        self.run_with_error_handling(
            self.backend.replace_war_linux,
            self.host, self.username, self.password, self.war_path, self.progress_signal.emit, self.speed_signal.emit
        )
        self.finished.emit()


class RestartPosThreadWindows(BaseWorkerThread):
    def __init__(self, backend: Backend, base_path: str, selected_version: str):
        super().__init__()
        self.backend = backend
        self.base_path = base_path
        self.selected_version = selected_version

    def run(self):
        self.run_with_error_handling(
            self.backend.restart_pos_windows,
            self.base_path, self.selected_version
        )


class ReplaceWarThreadWindows(BaseWorkerThread):
    def __init__(self, backend: Backend, base_path: str, selected_version: str, local_war_path: str):
        super().__init__()
        self.backend = backend
        self.base_path = base_path
        self.selected_version = selected_version
        self.local_war_path = local_war_path

    def run(self):
        self.run_with_error_handling(
            self.backend.replace_war_windows,
            self.base_path, self.selected_version, self.local_war_path
        )


class UpgradeThread(BaseWorkerThread):
    progress_signal = pyqtSignal(int)

    def __init__(self, backend: Backend, ssh, local_package_path: str, remote_target_path: str):
        super().__init__()
        self.backend = backend
        self.ssh = ssh
        self.local_package_path = local_package_path
        self.remote_target_path = remote_target_path

    def run(self):
        try:
            self.backend.upload_and_execute_upgrade(
                self.ssh,
                self.local_package_path,
                self.remote_target_path,
                self.progress_signal.emit
            )
        except Exception as e:
            self.error_signal.emit(f"升级过程中出错: {str(e)}")
        self.finished.emit()


class UploadUpgradePackageThread(BaseWorkerThread):
    progress_signal = pyqtSignal(int)
    speed_signal = pyqtSignal(str)  # 修改为str类型

    def __init__(self, backend: Backend, host: str, username: str, password: str, local_file: str):
        super().__init__()
        self.backend = backend
        self.host = host
        self.username = username
        self.password = password
        self.local_file = local_file

    def run(self):
        self.run_with_error_handling(
            self.backend.upload_and_extract_package,
            self.host, self.username, self.password, self.local_file, self.progress_signal.emit, self.speed_signal.emit
        )
        self.finished.emit()


class RestartTomcatThread(BaseWorkerThread):
    def __init__(self, backend: Backend, host: str, username: str, password: str):
        super().__init__()
        self.backend = backend
        self.host = host
        self.username = username
        self.password = password

    def run(self):
        self.run_with_error_handling(
            self.backend.restart_tomcat,
            self.host, self.username, self.password
        )
        self.finished.emit()


class BackupThread(BaseWorkerThread):
    progress_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()  # 改名，避免与 DownloadWarWorker 冲突

    def __init__(self, service, host, username, password):
        super().__init__()
        self.service = service
        self.host = host
        self.username = username
        self.password = password

    def run(self):
        try:
            def progress_callback(progress):
                self.progress_signal.emit(progress)
            def error_callback(err):
                self.error_signal.emit(err)
            def log_callback(msg):
                self.service.log(msg)
            self.service.backup_data(
                self.host,
                self.username,
                self.password,
                progress_callback=progress_callback,
                error_callback=error_callback,
                log_callback=log_callback
            )
            self.finished_signal.emit()
        except Exception as e:
            self.service.log(f"数据备份异常: {str(e)}")
            self.error_signal.emit(str(e))
            self.finished_signal.emit()


class RestoreThread(BaseWorkerThread):
    progress_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, service, host, username, password, item_name, is_zip):
        super().__init__()
        self.service = service
        self.host = host
        self.username = username
        self.password = password
        self.item_name = item_name
        self.is_zip = is_zip

    def run(self):
        try:
            def progress_callback(progress):
                self.progress_signal.emit(progress)
            def error_callback(err):
                self.error_signal.emit(err)
            def log_callback(msg):
                self.service.log(msg)
            self.service.restore_data(
                self.host,
                self.username,
                self.password,
                self.item_name,
                self.is_zip,
                progress_callback=progress_callback,
                error_callback=error_callback,
                log_callback=log_callback
            )
            self.finished_signal.emit()
        except Exception as e:
            self.service.log(f"数据恢复异常: {str(e)}")
            self.error_signal.emit(str(e))
            self.finished_signal.emit()


class SshTestThread(QThread):
    def __init__(self, service, host, username, password, callback):
        super().__init__()
        self.service = service
        self.host = host
        self.username = username
        self.password = password
        self.callback = callback

    def run(self):
        result = self.service.test_ssh(self.host, self.username, self.password)
        if result:
            self.callback(True, "连接成功")
        else:
            self.callback(False, "连接失败")


class PipelineUpgradeThread(QThread):
    finished = pyqtSignal(bool, str)
    progress_signal = pyqtSignal(int)
    speed_signal = pyqtSignal(str)
    progress_text_signal = pyqtSignal(str)

    def __init__(self, service, host, username, password, local_war_path, env, ui_ref):
        super().__init__()
        self.service = service
        self.host = host
        self.username = username
        self.password = password
        self.local_war_path = local_war_path
        self.env = env
        self.ui_ref = ui_ref

    def run(self):
        try:
            self._upload_and_extract_war()
            self._modify_config_files()
            self._restart_pos()
            self.finished.emit(True, "一键升级已完成！")
        except Exception as e:
            self._handle_exception(e)

    def _upload_and_extract_war(self):
        self._log_progress("正在上传/解压war包 ...")
        self.service.replace_war_linux(
            self.host, self.username, self.password, self.local_war_path,
            self.progress_signal.emit, self.speed_signal.emit
        )
        time.sleep(2)
        self.speed_signal.emit("")

    def _modify_config_files(self):
        self._log_progress("正在修改配置文件 ...")
        self.service.modify_remote_files(self.host, self.username, self.password, self.env)

    def _restart_pos(self):
        self._log_progress("正在重启POS ...")
        self.service.restart_pos_linux(self.host, self.username, self.password)

    def _log_progress(self, message):
        self.progress_text_signal.emit(message)
        self.ui_ref.set_progress_text(message)

    def _handle_exception(self, exception):
        self.speed_signal.emit("")
        self.finished.emit(False, f"一键升级过程中出错：{str(exception)}")


class PipelinePackageUpgradeThread(QObject, threading.Thread):
    finished = pyqtSignal(bool, str)  # (成功, 信息)
    progress_signal = pyqtSignal(int)
    speed_signal = pyqtSignal(str)  # 上传速率信号
    progress_text_signal = pyqtSignal(str)  # 更新进度文本

    def __init__(self, service, host, username, password, selected_dir, war_file, env, ui_ref=None):
        super().__init__()
        self.service = service
        self.host = host
        self.username = username
        self.password = password
        self.selected_dir = selected_dir
        self.war_file = war_file
        self.env = env
        self.ui_ref = ui_ref

    def run(self):
        try:
            def progress_callback(percent):
                self.progress_signal.emit(percent)
            def speed_callback(speed):
                self.speed_signal.emit(speed)
            def log_callback(msg):
                self.service.log(msg)
            def progress_text_callback(msg):
                if self.ui_ref:
                    self.progress_text_signal.emit(msg)
            self.service.pipeline_package_upgrade(
                self.host,
                self.username,
                self.password,
                self.selected_dir,
                self.war_file,
                self.env,
                progress_callback=progress_callback,
                speed_callback=speed_callback,
                log_callback=log_callback,
                progress_text_callback=progress_text_callback
            )
            self.finished.emit(True, "一键升级包升级已完成！")
        except Exception as e:
            self.service.log(f"升级异常: {str(e)}")
            self.finished.emit(False, f"升级过程中出错：{str(e)}")


class DownloadWarWorker(QThread):
    progress = pyqtSignal(int, str, int, int)  # percent, speed, downloaded, total
    finished = pyqtSignal(bool, str)

    def __init__(self, url, service: DownloadWarService, expected_size_mb=None):
        super().__init__()
        self.url = url
        self.service = service
        self.expected_size_mb = expected_size_mb

    def run(self):
        def cb(percent, speed=None, downloaded=None, total=None):
            self.progress.emit(percent, speed, downloaded, total)

        success, result = self.service.download_war(self.url, progress_callback=cb,
                                                    expected_size_mb=self.expected_size_mb)
        self.finished.emit(success, result)

class GenerateImgThread(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)

    def __init__(self, service, mode, width, height, mb, fmt):
        super().__init__()
        self.service = service
        self.mode = mode
        self.width = width
        self.height = height
        self.mb = mb
        self.fmt = fmt

    def run(self):
        self.progress_signal.emit(10)
        output_path, err = self.service.generate_image(self.mode, self.width, self.height, self.mb, self.fmt)
        self.progress_signal.emit(100)
        if err:
            self.finished_signal.emit("")
        else:
            self.finished_signal.emit(output_path)
