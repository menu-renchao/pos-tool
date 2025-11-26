import time

from PyQt6.QtCore import QThread, pyqtSignal

from pos_tool_new.download_war.download_war_service import DownloadWarService
from pos_tool_new.linux_pos.linux_service import LinuxService
from pos_tool_new.sms.sms_service import get_usable_phone_numbers_remote, get_latest_code_remote
from pos_tool_new.windows_file_config.file_config_win_service import WindowsFileConfigService, FileConfigItem
from pos_tool_new.windows_pos.windows_service import WindowsService


class BaseWorkerThread(QThread):
    # 统一信号定义
    progress_updated: pyqtSignal = pyqtSignal(int, object, object, object)  # 进度百分比, 速率, 已下载, 总大小
    progress_text_updated: pyqtSignal = pyqtSignal(str)  # 进度文本
    speed_updated: pyqtSignal = pyqtSignal(str)  # 速度信息
    status_updated: pyqtSignal = pyqtSignal(str)  # 状态信息
    error_occurred: pyqtSignal = pyqtSignal(str)  # 错误信息
    finished_updated: pyqtSignal = pyqtSignal(bool, str)  # 完成状态和消息

    def __init__(self):
        super().__init__()
        self._is_running = True

    def stop(self):
        """安全停止线程"""
        self._is_running = False
        self.quit()
        self.wait()

    def run(self):
        try:
            self._run_impl()
        except Exception as e:
            error_msg = f"执行失败: {str(e)}"
            self.error_occurred.emit(error_msg)
            self.finished_updated.emit(False, error_msg)

    def _run_impl(self):
        """子类需要实现的具体运行逻辑"""
        raise NotImplementedError("子类必须实现 _run_impl 方法")

    def run_with_error_handling(self, func, *args, **kwargs):
        """执行函数并捕获异常"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = f"操作失败: {str(e)}"
            self.error_occurred.emit(error_msg)
            raise


class RestartPosThreadLinux(BaseWorkerThread):
    def __init__(self, service: LinuxService, host: str, username: str, password: str):
        super().__init__()
        self.service = service
        self.host = host
        self.username = username
        self.password = password

    def _run_impl(self):
        self.progress_text_updated.emit("正在重启Linux POS服务...")
        self.run_with_error_handling(
            self.service.restart_pos_linux,
            self.host, self.username, self.password
        )
        self.progress_text_updated.emit("Linux POS服务重启完成")
        self.finished_updated.emit(True, "Linux POS服务重启完成")


class ReplaceWarThreadLinux(BaseWorkerThread):
    def __init__(self, service: LinuxService, host: str, username: str, password: str, war_path: str):
        super().__init__()
        self.service = service
        self.host = host
        self.username = username
        self.password = password
        self.war_path = war_path

    def _run_impl(self):
        self.progress_text_updated.emit("正在替换Linux WAR包...")

        def progress_callback(percent):
            try:
                percent = int(percent)
                self.progress_updated.emit(percent, None, None, None)
            except Exception:
                pass

        def speed_callback(speed_text):
            self.speed_updated.emit(speed_text)

        # 停止POS服务前先输出警告日志
        self.service.log("换包需停止pos服务,请在结束后自行重启", level="warning")
        # 先停止POS服务
        self.run_with_error_handling(
            self.service.stop_pos_linux,
            self.host, self.username, self.password
        )

        # 再替换WAR包
        self.run_with_error_handling(
            self.service.replace_war_linux,
            self.host, self.username, self.password, self.war_path,
            progress_callback=progress_callback,
            speed_callback=speed_callback
        )
        self.progress_text_updated.emit("Linux WAR包替换完成")
        self.finished_updated.emit(True, "Linux WAR包替换完成")


class RestartPosThreadWindows(BaseWorkerThread):
    def __init__(self, service: WindowsService, base_path: str, selected_version: str):
        super().__init__()
        self.service = service
        self.base_path = base_path
        self.selected_version = selected_version

    def _run_impl(self):
        self.progress_text_updated.emit("正在重启Windows POS服务...")
        self.run_with_error_handling(
            self.service.restart_pos_windows,
            self.base_path, self.selected_version
        )
        self.progress_text_updated.emit("Windows POS服务重启完成")
        self.finished_updated.emit(True, "Windows POS服务重启完成")


class ReplaceWarThreadWindows(BaseWorkerThread):
    def __init__(self, service: WindowsService, base_path: str, selected_version: str, local_war_path: str):
        super().__init__()
        self.service = service
        self.base_path = base_path
        self.selected_version = selected_version
        self.local_war_path = local_war_path

    def _run_impl(self):
        self.progress_text_updated.emit("正在停止Windows POS服务...")
        self.service.stop_pos_windows()
        self.progress_text_updated.emit("正在替换Windows WAR包...")
        self.run_with_error_handling(
            self.service.replace_war_windows,
            self.base_path, self.selected_version, self.local_war_path
        )
        self.progress_text_updated.emit("Windows WAR包替换完成")
        self.finished_updated.emit(True, "Windows WAR包替换完成")


class UpgradeThread(BaseWorkerThread):
    def __init__(self, service: LinuxService, ssh, local_package_path: str, remote_target_path: str):
        super().__init__()
        self.service = service
        self.ssh = ssh
        self.local_package_path = local_package_path
        self.remote_target_path = remote_target_path

    def _run_impl(self):
        self.progress_text_updated.emit("开始升级流程...")

        def progress_callback(percent):
            self.progress_updated.emit(percent, None, None, None)

        self.run_with_error_handling(
            self.service.upload_and_execute_upgrade,
            self.ssh,
            self.local_package_path,
            self.remote_target_path,
            progress_callback
        )
        self.progress_text_updated.emit("升级流程完成")
        self.finished_updated.emit(True, "升级流程完成")


class UploadUpgradePackageThread(BaseWorkerThread):
    def __init__(self, service: LinuxService, host: str, username: str, password: str, local_file: str):
        super().__init__()
        self.service = service
        self.host = host
        self.username = username
        self.password = password
        self.local_file = local_file

    def _run_impl(self):
        self.progress_text_updated.emit("开始上传升级包...")

        def progress_callback(percent):
            self.progress_updated.emit(percent, None, None, None)

        def speed_callback(speed):
            self.speed_updated.emit(speed)

        self.run_with_error_handling(
            self.service.upload_and_extract_package,
            self.host, self.username, self.password, self.local_file,
            progress_callback, speed_callback
        )
        self.progress_text_updated.emit("升级包上传完成")
        self.finished_updated.emit(True, "升级包上传完成")


class RestartTomcatThread(BaseWorkerThread):
    def __init__(self, service: LinuxService, host: str, username: str, password: str):
        super().__init__()
        self.service = service
        self.host = host
        self.username = username
        self.password = password

    def _run_impl(self):
        self.progress_text_updated.emit("正在重启Tomcat服务...")
        self.run_with_error_handling(
            self.service.restart_tomcat,
            self.host, self.username, self.password
        )
        self.progress_text_updated.emit("Tomcat服务重启完成")
        self.finished_updated.emit(True, "Tomcat服务重启完成")


class BackupThread(BaseWorkerThread):
    def __init__(self, service, host, username, password):
        super().__init__()
        self.service = service
        self.host = host
        self.username = username
        self.password = password

    def _run_impl(self):
        self.progress_text_updated.emit("开始数据备份...")

        def progress_callback(progress):
            self.progress_updated.emit(progress, None, None, None)

        def error_callback(err):
            self.error_occurred.emit(err)

        def log_callback(msg, level="info"):
            self.status_updated.emit(msg)
            self.service.log(msg, level=level)

        self.run_with_error_handling(
            self.service.backup_data,
            self.host,
            self.username,
            self.password,
            progress_callback=progress_callback,
            error_callback=error_callback,
            log_callback=log_callback
        )
        self.progress_text_updated.emit("数据备份完成")
        self.finished_updated.emit(True, "数据备份完成")


class RestoreThread(BaseWorkerThread):
    def __init__(self, service, host, username, password, item_name, is_zip):
        super().__init__()
        self.service = service
        self.host = host
        self.username = username
        self.password = password
        self.item_name = item_name
        self.is_zip = is_zip

    def _run_impl(self):
        self.progress_text_updated.emit("开始数据恢复...")

        def progress_callback(progress):
            self.progress_updated.emit(progress, None, None, None)

        def error_callback(err):
            self.error_occurred.emit(err)

        def log_callback(msg, level="info"):
            self.status_updated.emit(msg)
            self.service.log(msg, level=level)

        self.run_with_error_handling(
            self.service.restore_data,
            self.host,
            self.username,
            self.password,
            self.item_name,
            self.is_zip,
            progress_callback=progress_callback,
            error_callback=error_callback,
            log_callback=log_callback
        )
        self.progress_text_updated.emit("数据恢复完成")
        self.finished_updated.emit(True, "数据恢复完成")


class SshTestThread(BaseWorkerThread):
    def __init__(self, service, host, username, password):
        super().__init__()
        self.service = service
        self.host = host
        self.username = username
        self.password = password

    def _run_impl(self):
        try:
            result = self.service.test_ssh(self.host, self.username, self.password)
            if result:
                self.finished_updated.emit(True, "SSH连接测试成功")
            else:
                self.finished_updated.emit(False, "SSH连接测试失败")
        except Exception as e:
            self.finished_updated.emit(False, f"SSH连接测试异常: {str(e)}")


class PipelineUpgradeThread(BaseWorkerThread):
    def __init__(self, service, host, username, password, local_war_path, env, ui_ref=None):
        super().__init__()
        self.service = service
        self.host = host
        self.username = username
        self.password = password
        self.local_war_path = local_war_path
        self.env = env
        self.ui_ref = ui_ref

    def _run_impl(self):
        try:
            self._stop_pos()
            self._upload_and_extract_war()
            self._modify_config_files()
            self._start_pos()
            self.finished_updated.emit(True, "一键升级完成")
        except Exception as e:
            self._handle_exception(e)

    def _upload_and_extract_war(self):
        self.progress_text_updated.emit("正在上传/解压WAR包...")

        def progress_callback(percent):
            self.progress_updated.emit(percent, None, None, None)

        def speed_callback(speed):
            self.speed_updated.emit(speed)

        self.service.replace_war_linux(
            self.host, self.username, self.password, self.local_war_path,
            progress_callback, speed_callback
        )
        time.sleep(2)
        self.speed_updated.emit("")

    def _modify_config_files(self):
        self.progress_text_updated.emit("正在修改配置文件...")
        self.service.modify_remote_files(self.host, self.username, self.password, self.env)

    def _start_pos(self):
        self.progress_text_updated.emit("正在启动POS服务...")
        self.service.start_pos_linux(self.host, self.username, self.password)

    def _stop_pos(self):
        self.progress_text_updated.emit("正在停止POS服务...")
        self.service.stop_pos_linux(self.host, self.username, self.password)

    def _handle_exception(self, exception):
        self.speed_updated.emit("")
        error_msg = f"一键升级过程中出错：{str(exception)}"
        self.error_occurred.emit(error_msg)
        raise Exception(error_msg)


class PipelinePackageUpgradeThread(BaseWorkerThread):
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

    def _run_impl(self):
        def progress_callback(percent):
            self.progress_updated.emit(percent, None, None, None)

        def speed_callback(speed):
            self.speed_updated.emit(speed)

        def log_callback(msg, level="info"):
            self.status_updated.emit(msg)
            self.service.log(msg, level=level)

        def progress_text_callback(msg):
            self.progress_text_updated.emit(msg)
            if self.ui_ref and hasattr(self.ui_ref, 'set_progress_text'):
                self.ui_ref.set_progress_text(msg)

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
        self.finished_updated.emit(True, "一键包升级完成")


class DownloadWarWorker(BaseWorkerThread):
    def __init__(self, url, service: DownloadWarService, expected_size_mb=None):
        super().__init__()
        self.url = url
        self.service = service
        self.expected_size_mb = expected_size_mb
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def is_cancelled(self):
        return self._is_cancelled

    def _run_impl(self):
        self.progress_text_updated.emit("开始下载WAR包...")
        try:
            def progress_callback(percent, speed=None, downloaded=None, total=None):
                self.progress_updated.emit(percent, speed, downloaded, total)
                if speed:
                    self.speed_updated.emit(speed)
                if downloaded is not None and total is not None:
                    self.status_updated.emit(f"下载进度: {downloaded}/{total} bytes")

            success, result = self.service.download_war(
                self.url,
                progress_callback=progress_callback,
                expected_size_mb=self.expected_size_mb,
                is_cancelled=self.is_cancelled
            )

            if not success:
                self.service.log(f"WAR包下载失败: {result}", level="error")
                self.finished_updated.emit(False, f"WAR包下载失败: {result}")
            else:
                self.finished_updated.emit(True, result)
        except Exception as e:
            self.service.log(f"WAR包下载异常: {e}", level="error")
            self.finished_updated.emit(False, f"WAR包下载异常: {e}")


class GenerateImgThread(BaseWorkerThread):
    def __init__(self, service, mode, width, height, mb, fmt):
        super().__init__()
        self.service = service
        self.mode = mode
        self.width = width
        self.height = height
        self.mb = mb
        self.fmt = fmt

    def _run_impl(self):
        self.progress_updated.emit(10, None, None, None)
        self.progress_text_updated.emit("开始生成图片...")

        output_path, err = self.service.generate_image(self.mode, self.width, self.height, self.mb, self.fmt)

        self.progress_updated.emit(100, None, None, None)
        if err:
            raise Exception(f"图片生成失败: {err}")
        else:
            self.status_updated.emit(f"图片生成成功: {output_path}")


class ScanPosWorkerThread(BaseWorkerThread):
    scan_progress: pyqtSignal = pyqtSignal(int, str)  # 扫描进度百分比和当前IP
    scan_result: pyqtSignal = pyqtSignal(dict)  # 单个扫描结果
    scan_finished: pyqtSignal = pyqtSignal(list)  # 扫描完成后的结果列表

    def __init__(self, service, port=22080):
        super().__init__()
        self.service = service
        self.port = port
        self._results = []

    def _run_impl(self):
        self.service.scan_network(self, self.port)


class RandomMailLoadThread(BaseWorkerThread):
    mails_loaded = pyqtSignal(list)

    def __init__(self, service, parent=None):
        super().__init__()
        self.service = service
        self.parent = parent

    def _run_impl(self):
        # 调用邮件服务获取邮件列表
        emails = self.service.get_emails()
        self.mails_loaded.emit(emails)


class ReusableMailContentThread(BaseWorkerThread):
    mail_content_loaded = pyqtSignal(str, str)  # html, mail_id

    def __init__(self, service):
        super().__init__()
        self.service = service
        self._mail_id = None
        self._pending = False
        self._is_running = True

    def load_mail(self, mail_id):
        self._mail_id = mail_id
        self._pending = True
        if not self.isRunning():
            self.start()

    def _run_impl(self):
        while self._pending and self._is_running:
            self._pending = False
            mail_id = self._mail_id
            try:
                html = self.service.get_email_content(mail_id)
                self.mail_content_loaded.emit(html, mail_id)
            except Exception as e:
                self.error_occurred.emit(str(e))

    def stop(self):
        self._is_running = False


class DatabaseConnectThread(BaseWorkerThread):
    def __init__(self, license_service, host):
        super().__init__()
        self.license_service = license_service
        self.host = host

    def _run_impl(self):
        try:
            success, message = self.license_service.connect_database(self.host)
            self.finished_updated.emit(success, message)
        except Exception as e:
            self.error_occurred.emit(str(e))


class DbConfigWorkerThread(BaseWorkerThread):
    def __init__(self, service, config_name, enabled, db_params):
        super().__init__()
        self.service = service
        self.config_name = config_name
        self.enabled = enabled
        self.db_params = db_params

    def _run_impl(self):
        self.service.set_config(self.config_name, self.enabled, self.db_params)


class FileConfigModifyThread(BaseWorkerThread):
    def __init__(self, service, host, username, password, config_item, env):
        super().__init__()
        self.service = service
        self.host = host
        self.username = username
        self.password = password
        self.config_item = config_item
        self.env = env

    def _run_impl(self):
        self.progress_updated.emit(0, None, None, None)
        self.progress_text_updated.emit(f"正在修改配置文件: {self.config_item.name}")

        success, message = self.service.execute_config_modification(
            self.host, self.username, self.password, self.config_item, self.env
        )

        self.progress_updated.emit(100, None, None, None)
        if success:
            self.status_updated.emit(message)
        else:
            self.error_occurred.emit(message)
        # 补充：无论成功或失败都发射 finished_updated 信号，确保批量流程继续
        self.finished_updated.emit(success, message)


class WindowsFileModifyThread(BaseWorkerThread):
    """Windows文件修改线程"""

    def __init__(self, service: WindowsFileConfigService, connection_type: str,
                 host: str, username: str, password: str, file_config: FileConfigItem, env: str, select_version: str,
                 base_path: str):
        super().__init__()
        self.service: WindowsFileConfigService = service
        self.connection_type = connection_type
        self.host = host
        self.username = username
        self.password = password
        self.file_config = file_config
        self.env = env
        self.select_version = select_version
        self.base_path = base_path

    def _run_impl(self):
        try:
            self.progress_text_updated.emit(f"开始执行配置: {self.file_config.name}")
            self.progress_updated.emit(10, None, None, None)

            if self.connection_type == "local":
                success, message = self._modify_local_file()
            else:
                success, message = self._modify_remote_file()

            self.progress_updated.emit(100, None, None, None)
            self.finished_updated.emit(success, message)

        except Exception as e:
            self.error_occurred.emit(f"执行失败: {str(e)}")
            self.finished_updated.emit(False, f"执行失败: {str(e)}")

    def _modify_local_file(self) -> tuple:
        """修改本地文件"""
        file_path = self.file_config.get_absolute_path(self.select_version, self.base_path)
        try:
            import os
            if not os.path.exists(file_path):
                user = os.getlogin() if hasattr(os, 'getlogin') else 'unknown'
                msg = f"本地文件不存在: {file_path}，当前用户: {user}。请检查路径拼接是否正确，文件是否已部署。"

                from pos_tool_new.utils.log_manager import global_log_manager
                self.service.log(msg, "error")
                return False, msg
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            from pos_tool_new.utils.log_manager import global_log_manager
            self.service.log(f"[修改前内容] {file_path}:\n{content}", "debug")
            self.progress_updated.emit(50, None, None, None)
            new_content = self.service.modify_file_content(content, self.file_config, self.env, self.select_version)

            self.service.log(f"[修改后内容] {file_path}:\n{new_content}", "debug")
            import os
            if file_path.lower().endswith('.json'):
                import json
                try:
                    if json.loads(content) == json.loads(new_content):
                        msg = "文件内容无需修改"
                        self.service.log(msg, "info")
                        return True, msg
                except Exception:
                    pass  # 如果解析失败则回退到原始比较
            if content == new_content:
                msg = "文件内容无需修改"
                self.service.log(msg, "info")
                return True, msg
            # 移除备份逻辑，直接写入新内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            self.progress_updated.emit(90, None, None, None)
            msg = f"本地文件修改成功: {file_path}"
            self.service.log(msg, "info")
            return True, msg
        except Exception as e:
            import os
            user = os.getlogin() if hasattr(os, 'getlogin') else 'unknown'
            msg = f"修改本地文件失败: {file_path}，当前用户: {user}，错误: {str(e)}"
            if "Permission denied" in str(e):
                msg += "。请检查本地用户权限，确保有读写该文件的权限。"
            elif "No such file" in str(e):
                msg += "。请检查路径拼接是否正确，文件是否已部署。"

            from pos_tool_new.utils.log_manager import global_log_manager
            self.service.log(msg, "error")
            return False, msg

    def _modify_remote_file(self) -> tuple:
        """修改远程文件（通过OpenSSH）"""
        file_path = self.file_config.get_absolute_path(self.select_version, self.base_path)
        try:
            import paramiko
            self.progress_text_updated.emit("正在连接远程主机...")
            self.progress_updated.emit(20, None, None, None)
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.host, username=self.username, password=self.password)
            self.progress_updated.emit(40, None, None, None)
            self.progress_text_updated.emit("正在读取远程文件...")
            sftp = ssh.open_sftp()
            try:
                with sftp.file(file_path, 'r') as f:
                    content = f.read().decode('utf-8')
            except Exception as e:
                msg = f"远程文件不存在或无法读取: {file_path}，远程用户: {self.username}，错误: {str(e)}"
                if "Permission denied" in str(e):
                    msg += "。请检查远程用户权限，确保有读写该文件的权限。"
                elif "No such file" in str(e):
                    msg += "。请检查路径拼接是否正确，文件是否已部署。"

                from pos_tool_new.utils.log_manager import global_log_manager
                self.service.log(msg, "error")
                return False, msg

            from pos_tool_new.utils.log_manager import global_log_manager
            self.service.log(f"[修改前内容] {file_path}:\n{content}", "debug")
            self.progress_updated.emit(60, None, None, None)
            self.progress_text_updated.emit("正在修改文件内容...")
            new_content = self.service.modify_file_content(content, self.file_config, self.env, self.select_version)

            self.service.log(f"[修改后内容] {file_path}:\n{new_content}", "debug")
            if file_path.lower().endswith('.json'):
                import json
                try:
                    if json.loads(content) == json.loads(new_content):
                        ssh.close()
                        msg = "文件内容无需修改"
                        self.service.log(msg, "info")
                        return True, msg
                except Exception:
                    pass  # 如果解析失败则回退到原始比较
            if content == new_content:
                ssh.close()
                msg = "文件内容无需修改"
                self.service.log(msg, "info")
                return True, msg
            self.progress_updated.emit(80, None, None, None)
            self.progress_text_updated.emit("正在写入远程文件...")
            try:
                # 移除远程备份逻辑，直接写入新内容
                with sftp.file(file_path, 'w') as f:
                    f.write(new_content.encode('utf-8'))
            except Exception as e:
                msg = f"写入远程文件失败: {file_path}，远程用户: {self.username}，错误: {str(e)}"
                if "Permission denied" in str(e):
                    msg += "。请检查远程用户权限，确保有写该文件的权限。"

                self.service.log(msg, "error")
                return False, msg
            ssh.close()
            self.progress_updated.emit(100, None, None, None)
            msg = f"远程文件修改成功: {file_path}"

            self.service.log(msg, "info")
            return True, msg
        except Exception as e:
            msg = f"远程文件操作失败: {str(e)}"

            from pos_tool_new.utils.log_manager import global_log_manager
            self.service.log(msg, "error")
            return False, msg


class RemoteTailLogThread(BaseWorkerThread):
    log_updated = pyqtSignal(str)
    connection_status = pyqtSignal(str, str)  # 新增：连接状态信号

    def __init__(self, service, host, username, password, remote_file, interval=0.5):
        super().__init__()
        self.service = service
        self.host = host
        self.username = username
        self.password = password
        self.remote_file = remote_file
        self.interval = interval
        self._running = True

    def stop(self):
        self._running = False

    def _run_impl(self):
        self.connection_status.emit("connecting", "连接中...")  # 发射连接中信号

        def stop_flag():
            return not self._running

        def on_log(line):
            # 第一次收到日志时，认为连接成功
            if not hasattr(self, '_connected'):
                self._connected = True
                self.connection_status.emit("connected", "已连接")
            self.log_updated.emit(line)

        try:
            self.service.stream_remote_log_tail(
                self.host, self.username, self.password, self.remote_file, self.interval, on_log, stop_flag
            )
        except Exception as e:
            self.connection_status.emit("error", f"连接失败: {str(e)}")


class ConfigRunThread(BaseWorkerThread):
    def __init__(self, service, items, db_params, parent=None):
        super().__init__()
        self.service = service
        self.items = items
        self.db_params = db_params

    def _run_impl(self):
        try:
            result = self.service.set_config(self.items, self.db_params)
            item = self.items[0]
            msg = f"{item.description}: {'需重启生效' if result.get(item.description) else '立即生效'}"
            self.status_updated.emit(msg)
            self.finished_updated.emit(True, msg)
        except Exception as e:
            err_msg = f"执行配置项时发生错误: {str(e)}"
            self.error_occurred.emit(err_msg)
            self.finished_updated.emit(False, err_msg)


class SmsWorkerThread(BaseWorkerThread):
    phone_numbers_ready = pyqtSignal(list, str)
    messages_ready = pyqtSignal(list, str)

    def __init__(self):
        super().__init__()
        self.operation = None
        self.phone_number = None
        self.keyword = None
        self.count = None

    def set_refresh_operation(self):
        self.operation = "refresh"

    def set_query_operation(self, phone_number, keyword, count):
        self.operation = "query"
        self.phone_number = phone_number
        self.keyword = keyword
        self.count = count

    def run(self):
        if self.operation == "refresh":
            self.refresh_phone_numbers()
        elif self.operation == "query":
            self.query_messages()

    def refresh_phone_numbers(self):
        try:
            phone_numbers = get_usable_phone_numbers_remote()
            if isinstance(phone_numbers, list):
                self.phone_numbers_ready.emit(phone_numbers, "")
            else:
                self.phone_numbers_ready.emit([], phone_numbers)
        except Exception as e:
            self.phone_numbers_ready.emit([], str(e))

    def query_messages(self):
        import re
        try:
            phone_number = self.phone_number.replace('+', '').replace(' ', '')
            result = get_latest_code_remote(phone_number, self.keyword, self.count)
            if not result:
                self.messages_ready.emit([], f"未找到包含 '{self.keyword}' 的短信")
                return
            messages = []
            for msg in result.split("\n\n"):
                from_match = re.search(r"From: (.+?),", msg)
                time_match = re.search(r"Time: (.+?),", msg)
                content_match = re.search(r"Content: (.+)", msg)
                if from_match and time_match and content_match:
                    messages.append({
                        'sender': from_match.group(1),
                        'time': time_match.group(1),
                        'content': content_match.group(1)
                    })
            self.messages_ready.emit(messages, "")
        except Exception as e:
            self.messages_ready.emit([], str(e))
