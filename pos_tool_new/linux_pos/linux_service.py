import os
import posixpath
import re
import tempfile
import time
from typing import List, Tuple, Optional, Callable

import paramiko

from pos_tool_new.backend import Backend
from pos_tool_new.utils import log_manager


class LinuxService(Backend):
    # 常量定义
    TOMCAT_HOME = "/opt/tomcat7"
    WEBAPPS_DIR = f"{TOMCAT_HOME}/webapps"
    BACKUP_DIR = "/opt/backup"
    MENU_HOME = "/home/menu"

    def __init__(self):
        super().__init__()
        self.log_manager = log_manager

    @staticmethod
    def _validate_connection_params(host: str, username: str, password: str) -> None:
        """验证连接参数的有效性"""
        if not all([host, username, password]):
            raise ValueError("主机、用户名和密码不能为空")

        # 验证IP地址格式
        ip_pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
        match = re.match(ip_pattern, host)
        if not match:
            raise ValueError("参数错误", "请填写有效的主机IP地址！")

        # 验证IP地址各部分是否在有效范围内
        if not all(0 <= int(part) <= 255 for part in match.groups()):
            raise ValueError("参数错误", "请填写有效的主机IP地址！")

    def test_ssh(self, host: str, username: str, password: str) -> bool:
        """测试SSH连接是否成功"""
        try:
            self.log(f"正在尝试连接到 {username}@{host}...", level="info")
            with paramiko.SSHClient() as ssh:
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(host, username=username, password=password, timeout=10)
                _, stdout, _ = ssh.exec_command("echo '连接测试成功'")
                output = stdout.read().decode().strip()

                if output == "连接测试成功":
                    self.log("连接成功!", level="success")
                    return True
                else:
                    self.log("连接失败，返回意外输出", level="error")
                    return False
        except Exception as e:
            self.log(f"连接失败: {str(e)}", level="error")
            return False

    def _connect_ssh(self, host: str, username: str, password: str) -> paramiko.SSHClient:
        """建立SSH连接"""
        self._validate_connection_params(host, username, password)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=username, password=password, timeout=10)
        return ssh

    @staticmethod
    def _execute_command(ssh: paramiko.SSHClient, command: str,
                         timeout: int = 30) -> Tuple[str, str, int]:
        """执行远程命令并返回结果"""
        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        return out, err, exit_status

    def _check_file_exists(self, ssh: paramiko.SSHClient, remote_path: str) -> bool:
        """检查远程文件是否存在"""
        out, _, exit_status = self._execute_command(ssh, f"[ -f '{remote_path}' ] && echo '存在' || echo '未找到'")
        return out == '存在' and exit_status == 0

    def _read_remote_file(self, ssh: paramiko.SSHClient, remote_path: str) -> str:
        """读取远程文件内容"""
        out, err, exit_status = self._execute_command(ssh, f"cat '{remote_path}'")
        if exit_status != 0:
            raise IOError(f"无法读取文件 {remote_path}: {err}")
        return out

    def _write_remote_file(self, ssh: paramiko.SSHClient, remote_path: str, content: str) -> None:
        """写入内容到远程文件"""
        # 使用SFTP上传文件内容
        with ssh.open_sftp() as sftp:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name

            try:
                # 上传文件
                sftp.put(temp_path, remote_path)
            finally:
                # 清理临时文件
                os.unlink(temp_path)

    def stop_pos_linux(self, host: str, username: str, password: str) -> None:
        """远程停止 MenuSifu POS 应用相关进程"""
        try:
            self.log("正在停止远程POS服务...", level="info")
            processes = [
                ("[INFO] Killing menusifu_pos_extention", "/opt/menusifu/menusifu_pos_extention"),
                ("[INFO] Killing do_pos_start", "/opt/POS/do_pos_start"),
                ("[INFO] Killing show_pos_icon", "/opt/POS/show_pos_icon"),
                ("[INFO] Killing tomcat7", "tomcat7"),
            ]
            with self._connect_ssh(host, username, password) as ssh:
                for info, process in processes:
                    self.log(info, level="info")
                    cmd = f"echo '{password}' | sudo -S pkill -9 -f '{process}'"
                    out, err, _ = self._execute_command(ssh, cmd, timeout=240)
                    if out:
                        self.log(out, level="info")
                    if err:
                        self.log(f"错误: {err}", level="error")
                # 新增停止 tomcat.service 的逻辑
                self.log("[INFO] Stopping tomcat.service via systemctl", level="info")
                cmd = f"echo '{password}' | sudo -S systemctl stop tomcat.service"
                out, err, _ = self._execute_command(ssh, cmd, timeout=240)
                if out:
                    self.log(out, level="info")
                if err:
                    self.log(f"错误: {err}", level="error")
            self.log("停止完成。", level="success")
        except Exception as e:
            self.log(f"停止过程中出错: {str(e)}", level="error")
            raise

    def start_pos_linux(self, host: str, username: str, password: str) -> None:
        """远程启动 MenuSifu POS 应用"""
        try:
            self.log("正在启动远程POS服务...", level="info")
            with self._connect_ssh(host, username, password) as ssh:
                cmd = "DISPLAY=:0 /usr/local/bin/pos_start"
                out, err, _ = self._execute_command(ssh, cmd, timeout=240)
                if out:
                    self.log(out, level="info")
                if err:
                    self.log(f"错误: {err}", level="error")
            self.log("启动完成。", level="success")
        except Exception as e:
            self.log(f"启动过程中出错: {str(e)}", level="error")
            raise

    def restart_pos_linux(self, host: str, username: str, password: str) -> None:
        """远程一键重启 MenuSifu POS 应用"""
        try:
            self.stop_pos_linux(host, username, password)
            self.start_pos_linux(host, username, password)
        except Exception as e:
            self.log(f"重启过程中出错: {str(e)}", level="error")
            raise

    def _upload_file_with_progress(self, sftp, local_path: str, remote_path: str,
                                   progress_callback: Optional[Callable] = None,
                                   speed_callback: Optional[Callable] = None,
                                   progress_range: Tuple[int, int] = (0, 100)) -> None:
        """带进度显示的文件上传"""
        file_size = os.path.getsize(local_path)
        chunk_size = 256 * 1024  # 256KB
        uploaded = 0
        low, high = progress_range

        with open(local_path, 'rb') as local_file, sftp.file(remote_path, 'wb') as remote_file:
            last_time = time.time()
            last_uploaded = 0

            while chunk := local_file.read(chunk_size):
                remote_file.write(chunk)
                uploaded += len(chunk)

                # 更新进度
                if progress_callback:
                    current_progress = min(low + int(uploaded / file_size * (high - low)), high)
                    progress_callback(current_progress)

                # 更新速度
                current_time = time.time()
                if speed_callback and (current_time - last_time >= 0.5):
                    speed = (uploaded - last_uploaded) / (current_time - last_time)
                    speed_text = f"上传速率：{speed / 1024 / 1024:.2f} MB/s"
                    speed_callback(speed_text)
                    last_time = current_time
                    last_uploaded = uploaded

    def replace_war_linux(self, host: str, username: str, password: str, local_war_path: str,
                          progress_callback: Optional[Callable] = None,
                          speed_callback: Optional[Callable] = None) -> None:
        """替换远程服务器上的war包"""
        try:
            self.log(f"连接到 {host} ...")
            with self._connect_ssh(host, username, password) as ssh:
                remote_dir = self.WEBAPPS_DIR
                remote_war = f"{remote_dir}/kpos.war"
                remote_kpos = f"{remote_dir}/kpos"
                if not local_war_path or not os.path.isfile(local_war_path):
                    self.log("本地war包路径无效", level="error")
                    raise ValueError("本地war包路径无效")

                # 删除旧war包
                self._execute_command(ssh, f"rm -f {remote_war}")
                self.log("旧war包已删除", "warning")
                if progress_callback:
                    progress_callback(20)

                # 上传新war包
                self.log("上传新war包...")
                with ssh.open_sftp() as sftp:
                    self._upload_file_with_progress(sftp, local_war_path, remote_war,
                                                    progress_callback, speed_callback, (20, 80))
                self.log("上传完成", "success")
                if progress_callback:
                    progress_callback(85)

                # 检查远程文件大小
                local_size = os.path.getsize(local_war_path)
                for _ in range(15):
                    out, _, exit_status = self._execute_command(ssh, f"stat -c %s {remote_war}")
                    if exit_status == 0 and out.strip().isdigit() and int(out.strip()) == local_size:
                        self.log(f"远程文件大小一致: {out.strip()} 字节", level="success")
                        break
                    time.sleep(1)
                else:
                    raise Exception("远程文件未就绪或大小不一致")

                # 删除旧kpos文件夹并解压新war包
                self._execute_command(ssh, f"rm -rf {remote_kpos}")
                self._execute_command(ssh, f"mkdir -p {remote_kpos}")
                self.log("解压新war包...")
                out, err, exit_status = self._execute_command(ssh, f"unzip -o -DD -q {remote_war} -d {remote_kpos}")
                if progress_callback:
                    progress_callback(100)
                time.sleep(5)  # 等待解压完成
                if exit_status == 0:
                    self.log("解压成功", level="success")
                    self.log("如果需要修改配置文件，可在此时操作，再重启POS。如不需要，则可以直接重启", level="warning")
                else:
                    real_errors = '\n'.join(
                        [line for line in err.splitlines() if not line.lower().startswith('warning:')])
                    self.log(f"解压失败: {real_errors}" if real_errors else "解压过程中有警告，但无致命错误", "warning")
        except Exception as e:
            self.log(f"替换war包出错: {str(e)}", level="error")
            raise

    def scan_upgrade_packages(self, ssh: paramiko.SSHClient, remote_base_path: str) -> List[str]:
        """扫描远程目标路径下符合条件的升级包，并按文件夹修改时间倒序排序"""
        try:
            self.log(f"正在扫描远程路径: {remote_base_path} ...", level="info")
            out, err, _ = self._execute_command(ssh, f"ls -d {remote_base_path}/1.8.0.30.* 2>/dev/null")
            if err:
                self.log(f"扫描目录时出错: {err}", level="error")
                return []

            valid_dirs = []
            for d in filter(None, out.splitlines()):
                is_valid, _, _ = self._execute_command(ssh, f"test -f {d}/update.sh && echo 'valid' || echo 'invalid'")
                if is_valid.strip() == "valid":
                    mtime_out, _, _ = self._execute_command(ssh, f"stat -c %Y {d}")
                    mtime = int(mtime_out.strip()) if mtime_out.strip().isdigit() else 0
                    valid_dirs.append((d, mtime))

            if not valid_dirs:
                self.log("未找到符合条件的升级包！", level="warning")
                return []

            return [d for d, _ in sorted(valid_dirs, key=lambda x: x[1], reverse=True)]
        except Exception as e:
            self.log(f"扫描远程路径时出错: {str(e)}", level="error")
            return []

    def upload_and_execute_upgrade(self, ssh: paramiko.SSHClient, local_package_path: str,
                                   remote_target_path: str, progress_callback: Optional[Callable] = None) -> None:
        """上传升级包并执行 update.sh"""
        try:
            if progress_callback:
                progress_callback(10)

            # 删除远程同名文件
            remote_package_path = posixpath.join(remote_target_path, os.path.basename(local_package_path))
            self.log(f"删除远程同名文件: {remote_package_path}", level="warning")
            self._execute_command(ssh, f"sudo rm -f {remote_package_path}")

            if progress_callback:
                progress_callback(40)

            # 上传升级包
            self.log(f"上传升级包到 {remote_package_path} ...", level="info")
            with ssh.open_sftp() as sftp:
                sftp.put(local_package_path, remote_package_path)
            self.log("上传完成", level="success")

            if progress_callback:
                progress_callback(70)

            # 执行 update.sh
            self.log("执行 update.sh ...", level="info")
            update_script = posixpath.join(remote_target_path, "update.sh")
            out, err, _ = self._execute_command(ssh, f"cd {remote_target_path} && sudo bash {update_script}")

            if out:
                self.log(out, level="info")
            if err:
                self.log(f"执行脚本时出错: {err}", level="error")
            else:
                self.log("升级完成", level="success")

            if progress_callback:
                progress_callback(100)
        except Exception as e:
            self.log(f"升级过程中出错: {str(e)}", level="error")
            if progress_callback:
                progress_callback(0)
            raise

    def get_file_md5(self, ssh: paramiko.SSHClient, remote_path: str) -> Optional[str]:
        """获取远程文件的 MD5 值"""
        try:
            out, err, _ = self._execute_command(ssh, f"md5sum {remote_path}")
            if err:
                self.log(f"获取 MD5 值时出错: {err}", level="error")
                return None
            return out.split()[0]  # 返回 MD5 值
        except Exception as e:
            self.log(f"获取 MD5 值过程中出错: {str(e)}", level="error")
            return None

    def scan_remote_logs(self, ssh: paramiko.SSHClient) -> List[str]:
        """扫描 /opt/tomcat7/logs 下所有 .log 文件"""
        out, _, _ = self._execute_command(ssh, 'ls /opt/tomcat7/logs/*.log 2>/dev/null')
        files = [f for f in out.splitlines() if f]
        return [os.path.basename(f) for f in files]

    def download_remote_log(self, ssh: paramiko.SSHClient, remote_file: str, local_dir: str) -> str:
        """下载指定远程日志文件到本地目录"""
        with ssh.open_sftp() as sftp:
            base = os.path.basename(remote_file)
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            name, ext = os.path.splitext(base)
            local_file = os.path.join(local_dir, f"{name}_{timestamp}{ext}")
            sftp.get(remote_file, local_file)
        return local_file

    def upload_and_extract_package(self, host: str, username: str, password: str, local_file: str,
                                   progress_callback: Optional[Callable] = None,
                                   speed_callback: Optional[Callable] = None) -> None:
        """上传并解压升级包"""
        try:
            if progress_callback:
                progress_callback(10)

            with self._connect_ssh(host, username, password) as ssh:
                remote_file = posixpath.join(self.MENU_HOME, os.path.basename(local_file))

                # 删除远程同名文件
                self.log(f"删除远程文件: {remote_file}", level="warning")
                self._execute_command(ssh, f"sudo rm -f {remote_file}")
                if progress_callback:
                    progress_callback(20)

                # 上传文件
                self.log(f"上传文件到 {remote_file} ...", level="info")
                with ssh.open_sftp() as sftp:
                    self._upload_file_with_progress(sftp, local_file, remote_file,
                                                    progress_callback, speed_callback, (20, 80))
                self.log("上传完成", level="success")
                if progress_callback:
                    progress_callback(85)

                # 解压文件前，删除同名文件夹
                folder_name = os.path.splitext(os.path.basename(remote_file))[0]
                self.log(f"删除同名文件夹: {self.MENU_HOME}/{folder_name}", level="warning")
                self._execute_command(ssh, f"sudo rm -rf {self.MENU_HOME}/{folder_name}")
                # 解压文件
                self.log("解压文件 ...", level="info")
                out, err, exit_status = self._execute_command(ssh,
                                                              f"sudo unzip -o {remote_file} -d {self.MENU_HOME} && sync")
                if exit_status == 0:
                    self.log("解压成功", level="success")
                else:
                    self.log(f"解压失败: {err}", level="error")
                if progress_callback:
                    progress_callback(100)
        except Exception as e:
            self.log(f"操作失败: {str(e)}", level="error")
            if progress_callback:
                progress_callback(0)

    def restart_tomcat(self, host: str, username: str, password: str) -> None:
        """远程重启Tomcat服务"""
        try:
            self.log("正在重启Tomcat服务...", level="info")
            with self._connect_ssh(host, username, password) as ssh:
                cmd = "sudo systemctl restart tomcat"
                stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
                stdin.write(f"{password}\n")
                stdin.flush()

                err = stderr.read().decode()
                if err:
                    self.log(f"错误: {err.strip()}", level="error")

                self.log("Tomcat服务已重启完成。", level="success")
        except Exception as e:
            self.log(f"重启Tomcat服务时出错: {str(e)}", level="error")

    def list_backup_items(self, host: str, username: str, password: str) -> List[str]:
        """列出备份目录下所有.zip和文件夹，按时间倒序"""
        try:
            with self._connect_ssh(host, username, password) as ssh:
                # 获取所有.zip和文件夹，按时间倒序
                out, _, _ = self._execute_command(
                    ssh, f"ls -dt {self.BACKUP_DIR}/*.zip {self.BACKUP_DIR}/*/ 2>/dev/null"
                )
                items = [
                    os.path.basename(line.strip().rstrip('/'))
                    for line in out.splitlines() if line.strip()
                ]
                return items
        except Exception as e:
            self.log(f"获取备份项失败: {str(e)}", level="error")
            return []

    def upgrade_with_package(self, host: str, username: str, password: str, local_package_path: str, env: str,
                             progress_callback: Optional[Callable] = None):
        """
        一键升级包升级主流程：上传升级包、解压、执行升级、进度分阶段递增
        """
        self.log(f"正在连接到 {host} ...")
        with self._connect_ssh(host, username, password) as ssh:
            remote_dir = "/home/menu"
            remote_zip = f"{remote_dir}/{os.path.basename(local_package_path)}"
            # 上传升级包
            self.log(f"上传升级包到 {remote_zip}")
            with ssh.open_sftp() as sftp:
                sftp.put(local_package_path, remote_zip)
            if progress_callback:
                progress_callback(20)
            # 解压升级包
            self.log(f"解压升级包 {remote_zip}")
            unzip_cmd = f"unzip -o {remote_zip} -d {remote_dir}"
            self._execute_command(ssh, unzip_cmd)
            if progress_callback:
                progress_callback(40)
            # 查找升级工具目录
            upgrade_dirs = self.scan_upgrade_packages(ssh, remote_dir)
            if not upgrade_dirs:
                raise Exception("未找到升级工具目录")
            # 选择第一个升级工具目录
            selected_dir = upgrade_dirs[0]
            self.log(f"执行升级工具: {selected_dir}")
            upgrade_cmd = f"cd {selected_dir} && sh upgrade.sh {env}"
            self._execute_command(ssh, upgrade_cmd)
            if progress_callback:
                progress_callback(60)
        self.log("升级包升级流程完成", level="success")

    def restore_data(self, host, username, password, item_name, is_zip, progress_callback=None, error_callback=None,
                     log_callback=None):
        """
        通过SSH连接到服务器，解压（如需要）并执行数据恢复。
        """
        try:
            if log_callback:
                log_callback(f"开始数据恢复: {host}, 恢复项: {item_name}")
            ssh = self._connect_ssh(host, username, password)
            folder_name = item_name
            progress = 5
            if progress_callback:
                progress_callback(progress)

            # 解压zip
            if is_zip:
                if log_callback:
                    log_callback(f"解压zip文件: {self.BACKUP_DIR}/{item_name}")
                unzip_cmd = f"sudo unzip {self.BACKUP_DIR}/{item_name} -d {self.BACKUP_DIR}/"
                stdin, stdout, stderr = ssh.exec_command(unzip_cmd)
                unzip_progress = progress
                while not stdout.channel.exit_status_ready():
                    time.sleep(0.5)
                    unzip_progress = min(unzip_progress + 5, 30)
                    if progress_callback:
                        progress_callback(unzip_progress)
                for line in stdout:
                    if log_callback:
                        log_callback(line.strip())
                err = stderr.read().decode()
                if err:
                    if log_callback:
                        log_callback(f"解压错误: {err}", "error")
                    if error_callback:
                        error_callback(err)
                folder_name = item_name.replace('.zip', '')
                progress = 30
                if progress_callback:
                    progress_callback(progress)

            # 修正：文件夹恢复时自动加斜杠
            if not is_zip and not folder_name.endswith('/'):
                folder_name = folder_name + '/'

            if log_callback:
                log_callback(f"执行dbrestore: cd {self.BACKUP_DIR} && dbrestore {folder_name}")
            restore_cmd = f"cd {self.BACKUP_DIR} && dbrestore {folder_name}"
            stdin, stdout, stderr = ssh.exec_command(restore_cmd)
            restore_progress = progress
            while not stdout.channel.exit_status_ready():
                time.sleep(0.5)
                restore_progress = min(restore_progress + 5, 95)
                if progress_callback:
                    progress_callback(restore_progress)

            for line in stdout:
                if log_callback:
                    log_callback(line.strip())

            err = stderr.read().decode()
            if err:
                if log_callback:
                    log_callback(f"恢复错误: {err}", "error")
                if error_callback:
                    error_callback(err)

            ssh.close()
            if log_callback:
                log_callback("数据恢复完成", "success")
            if progress_callback:
                progress_callback(100)

        except Exception as e:
            if log_callback:
                log_callback(f"数据恢复异常: {str(e)}", "error")
            if error_callback:
                error_callback(str(e))
            raise

    def backup_data(self, host, username, password, progress_callback=None, error_callback=None, log_callback=None):
        """
        通过SSH连接到服务器，执行数据备份。
        """
        try:
            if log_callback:
                log_callback(f"开始数据备份: {host}")
            ssh = self._connect_ssh(host, username, password)
            if log_callback:
                log_callback(f"执行备份脚本: cd {self.BACKUP_DIR} && sh backup.sh")
            cmd = f"cd {self.BACKUP_DIR} && sh backup.sh"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            progress = 5
            if progress_callback:
                progress_callback(progress)

            # 进度递增模拟
            while not stdout.channel.exit_status_ready():
                time.sleep(0.5)
                progress = min(progress + 3, 90)
                if progress_callback:
                    progress_callback(progress)

            for line in stdout:
                if log_callback:
                    log_callback(line.strip())

            err = stderr.read().decode()
            if err:
                if log_callback:
                    log_callback(f"备份脚本错误: {err}", "error")
                if error_callback:
                    error_callback(err)

            ssh.close()
            if log_callback:
                log_callback("数据备份完成", "success")
            if progress_callback:
                progress_callback(100)

        except Exception as e:
            if log_callback:
                log_callback(f"数据备份异常: {str(e)}", "error")
            if error_callback:
                error_callback(str(e))

    def modify_remote_files(self, host: str, username: str, password: str, env: str) -> None:
        """
        批量读取 file_config.json，依次调用 FileConfigService.execute_config_modification 进行远程配置修改。
        """
        from pos_tool_new.linux_file_config.file_config_linux_service import FileConfigService
        service = FileConfigService()
        configs = service.get_all_configs()
        for config_item in configs:
            if not getattr(config_item, 'enabled', True):
                continue
            service.log(f"开始批量修改配置项: {config_item.name}", level="info")
            success, message = service.execute_config_modification(host, username, password, config_item, env)
            if success:
                service.log(f"配置项修改成功: {config_item.name} - {message}", level="info")
            else:
                service.log(f"配置项修改失败: {config_item.name} - {message}", level="error")

    def pipeline_package_upgrade(self, host, username, password, selected_dir, war_file, env, progress_callback=None,
                                 speed_callback=None, log_callback=None, progress_text_callback=None):
        """
        一键升级包升级主流程：上传war包、执行升级脚本、修改配置、重启POS。
        """
        try:
            def log_and_emit(msg):
                if log_callback:
                    log_callback(msg)
                if progress_text_callback:
                    progress_text_callback(msg)

            log_and_emit("一键升级包升级开始")

            # 上传war包
            log_and_emit(f"正在上传kpos.war到{selected_dir} ...")
            with self._connect_ssh(host, username, password) as ssh:
                remote_war = f"{selected_dir}/kpos.war"
                with ssh.open_sftp() as sftp, open(war_file, 'rb') as f_src:
                    file_size = os.path.getsize(war_file)
                    uploaded, last_uploaded, start_time = 0, 0, time.time()
                    with sftp.file(remote_war, 'wb') as f_dst:
                        while True:
                            data = f_src.read(1024 * 1024)
                            if not data:
                                break
                            f_dst.write(data)
                            uploaded += len(data)
                            percent = int(uploaded / file_size * 40)  # 0~40区间
                            if progress_callback:
                                progress_callback(percent)
                            # 速率
                            elapsed = time.time() - start_time
                            if elapsed > 0 and speed_callback:
                                speed = (uploaded - last_uploaded) / elapsed / 1024 / 1024  # MB/s
                                speed_callback(f"上传速率：{speed:.2f} MB/s")
                                last_uploaded, start_time = uploaded, time.time()

                if speed_callback:
                    speed_callback("")  # 清空速率显示

            if progress_callback:
                progress_callback(40)

            # 执行升级脚本
            log_and_emit("正在执行升级脚本 ...")
            with self._connect_ssh(host, username, password) as ssh:
                self._execute_command(ssh, f"cd {selected_dir} && sh update.sh")

            if progress_callback:
                progress_callback(60)
            self.log("等待远程解压完成(5s) ...")
            time.sleep(5)  # 等待5秒
            if progress_callback:
                progress_callback(70)

            # 修改配置文件
            log_and_emit("正在修改配置文件 ...")
            self.modify_remote_files(host, username, password, env)

            if progress_callback:
                progress_callback(85)

            # 重启POS
            log_and_emit("正在重启POS ...")
            self.restart_pos_linux(host, username, password)

            if progress_callback:
                progress_callback(100)

            log_and_emit("一键升级包升级已完成！")

        except Exception as e:
            if log_callback:
                log_callback(f"升级异常: {str(e)}", "error")
            raise
