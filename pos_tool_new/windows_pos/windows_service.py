import os
import re
import shutil
import tempfile
import zipfile

from pos_tool_new.backend import Backend


class WindowsService(Backend):
    def __init__(self):
        super().__init__()
        self.file_patterns = [
            r"\tomcat\webapps\kpos\front\js\cloudUrlConfig.json",
            r"\tomcat\webapps\kpos\front2\json\cloudUrlConfig.json",
            r"\tomcat\webapps\kpos\front3\js\cloudUrlConfig.json",
            r"\tomcat\webapps\kpos\waitlist\cloudUrl.json"
        ]

    def scan_local(self, base_path, env):
        """Scan local directory for files that need to be modified."""
        if not os.path.isdir(base_path):
            self.log("基础目录不存在", level="error")
            return

        self.log(f"正在扫描 {base_path} 中的版本目录...", level="info")
        need_modify_files = []
        env_type = self.get_env_type_value(env)
        app_prop_pattern = rf"^application\.environmentType\s*=\s*{re.escape(env_type)}\s*$"

        for item in os.listdir(base_path):
            full_path = os.path.join(base_path, item)
            if not os.path.isdir(full_path):
                continue

            # Check files in the version directory
            for i, pattern in enumerate(self.file_patterns):
                file_path = os.path.join(full_path, pattern.lstrip('\\'))
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        new_content = self.replace_domain(content, env)
                        if new_content != content:
                            need_modify_files.append(file_path)
                    except Exception as e:
                        self.log(f"读取文件出错: {file_path} - {str(e)}", level="error")

            # Check cloudDatahub application.properties
            app_prop_path = os.path.join(
                full_path, r"tomcat\webapps\cloudDatahub\WEB-INF\classes\application.properties"
            )
            if os.path.isfile(app_prop_path):
                try:
                    with open(app_prop_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if not re.search(app_prop_pattern, content, re.MULTILINE):
                        need_modify_files.append(app_prop_path)
                except Exception as e:
                    self.log(f"读取文件出错: {app_prop_path} - {str(e)}", level="error")

        if not need_modify_files:
            self.log("未找到需要修改的文件", level="warning")
        else:
            self.log("需要修改的文件路径如下：", level="info")
            for f in need_modify_files:
                self.log(f, level="info")

    def _modify_local_file(self, file_path, env):
        """Modify a single local file with the new domain for the given environment."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            new_content = self.replace_domain(content, env)
            if new_content == content:
                self.log("文件本来就是目标值，无需修改", level="info")
                return False, True  # Not modified, already target

            # Write to temp file and replace original
            temp_fd, temp_path = tempfile.mkstemp()
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                os.replace(temp_path, file_path)
                self.log("文件已修改", level="info")
                return True, False  # Modified, not already target
            except Exception as e:
                self.log(f"写入临时文件失败: {str(e)}", level="error")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False, False
        except Exception as e:
            self.log(f"处理文件时出错: {file_path} - {str(e)}", level="error")
            return False, False

    def _modify_local_app_properties(self, version_path, env):
        """Modify or add environmentType in local application.properties."""
        app_prop_path = os.path.join(
            version_path, r"tomcat\webapps\cloudDatahub\WEB-INF\classes\application.properties"
        )
        if not os.path.isfile(app_prop_path):
            self.log("文件不存在", level="error")
            return False, False  # Not modified, not already target

        env_type = self.get_env_type_value(env)
        target_line = f"application.environmentType = {env_type}"

        try:
            with open(app_prop_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if already has the exact target line
            if re.search(rf"^application\.environmentType\s*=\s*{re.escape(env_type)}\s*$", content, re.MULTILINE):
                self.log("application.properties 本来就是目标值，无需修改", level="info")
                return False, True  # Not modified, already target

            # Check if has the environmentType setting but with different value
            if re.search(r"^application\.environmentType\s*=", content, re.MULTILINE):
                new_content = re.sub(
                    r"^application\.environmentType\s*=.*$",
                    target_line,
                    content,
                    flags=re.MULTILINE
                )
                with open(app_prop_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                self.log("application.properties 已修改", level="info")
                return True, False  # Modified, not already target
            else:
                # Append the setting if it doesn't exist
                with open(app_prop_path, 'a', encoding='utf-8') as f:
                    f.write('\n' + target_line + '\n')
                self.log("application.properties 已添加目标配置", level="info")
                return True, False  # Modified, not already target
        except Exception as e:
            self.log(f"处理 application.properties 出错: {str(e)}", level="error")
            return False, False

    def modify_local_files(self, base_path, env):
        """Modify all target files in the local directory for the given environment."""
        if not os.path.isdir(base_path):
            self.log("基础目录不存在", level="error")
            return

        modified_count = 0
        already_target_count = 0

        for version_dir in os.listdir(base_path):
            version_path = os.path.join(base_path, version_dir)
            if not os.path.isdir(version_path):
                continue
            self.log(f"正在处理版本: {version_dir}", level="info")

            # Process all configured files
            for i, pattern in enumerate(self.file_patterns):
                file_path = os.path.join(version_path, pattern.lstrip('\\'))
                self.log(f"正在检查文件 {i + 1}: {file_path}", level="info")
                if not os.path.isfile(file_path):
                    self.log("文件不存在", level="warning")
                    continue

                modified, already_target = self._modify_local_file(file_path, env)
                if modified:
                    modified_count += 1
                elif already_target:
                    already_target_count += 1

            # Process cloudDatahub application.properties
            modified_prop, already_target_prop = self._modify_local_app_properties(version_path, env)
            if modified_prop:
                modified_count += 1
            elif already_target_prop:
                already_target_count += 1

        self.log(f"本机pos已修改为{env}环境，已修改 {modified_count} 个文件，本来就是目标值 {already_target_count} 个。",
                 level="success")
        # 固定修正 expiration-management url，传递env
        self.fix_expiration_management_url(base_path, env)

    def replace_war_windows(self, base_path, selected_version, local_war_path):
        """替换 Windows 下的 kpos.war 包并解压"""
        try:
            version_path = os.path.join(base_path, selected_version)
            webapps_path = os.path.join(version_path, r"tomcat\webapps")
            war_path = os.path.join(webapps_path, "kpos.war")
            kpos_path = os.path.join(webapps_path, "kpos")

            # 删除旧文件
            if os.path.exists(war_path):
                self.log("正在删除旧的 kpos.war ...", level="warning")
                os.remove(war_path)
            if os.path.exists(kpos_path):
                self.log("正在删除旧的 kpos 目录 ...", level="warning")
                shutil.rmtree(kpos_path)

            # 复制新 WAR 包
            self.log("正在复制新的 kpos.war ...", level="info")
            shutil.copy(local_war_path, war_path)

            # 解压新 WAR 包
            self.log("正在解压新的 kpos.war ...", level="info")
            with zipfile.ZipFile(war_path, 'r') as zip_ref:
                zip_ref.extractall(kpos_path)
            self.log("解压完成", level="success")
            self.log("如需要修改环境，请使用修改功能，然后重启POS；如不需要修改环境，请直接重启POS。", level="warning")
            self.log(f"{selected_version} 替换 kpos.war 成功！", level="success")
        except Exception as e:
            self.log(f"替换 kpos.war 出错: {str(e)}", level="error")

    def restart_pos_windows(self, base_path, selected_version):
        """重启 Windows 下的 POS 应用"""
        try:
            version_path = os.path.join(base_path, selected_version)
            pos_exe_path = os.path.join(version_path, r"Menusifu Server Manager\Menusifu POS.exe")

            # 结束 POS 进程
            os.system('taskkill /IM "Menusifu POS.exe" /T /F')

            # 启动 POS
            os.startfile(pos_exe_path)
            self.log(f"{selected_version} POS 重启成功！", level="success")
        except Exception as e:
            self.log(f"重启 POS 出错: {str(e)}", level="error")

    # 效期管理
    def fix_expiration_management_url(self, base_path, env):
        """
        根据env修正 front2\json\cloudUrlConfig.json 里的 expiration-management 地址：
        QA/DEV -> https://wms.balamxqa.com/expiration-management
        PROD   -> https://wms.balamx.com/expiration-management
        """
        if not os.path.isdir(base_path):
            self.log("基础目录不存在", level="error")
            return
        if str(env).upper() in ("QA", "DEV"):
            target_url = "https://wms.balamxqa.com/expiration-management"
        else:
            target_url = "https://wms.balamx.com/expiration-management"
        changed = 0
        for version_dir in os.listdir(base_path):
            version_path = os.path.join(base_path, version_dir)
            if not os.path.isdir(version_path):
                continue
            json_path = os.path.join(version_path, r"tomcat\webapps\kpos\front2\json\cloudUrlConfig.json")
            if not os.path.isfile(json_path):
                continue
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # 无论原来是什么都替换为目标URL
                new_content = content.replace(
                    "https://wms.balamx.com/expiration-management", target_url
                ).replace(
                    "https://wms.balamxqa.com/expiration-management", target_url
                )
                if new_content != content:
                    with open(json_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    self.log(f"已修正: {json_path} -> {target_url}", level="success")
                    changed += 1
                else:
                    self.log(f"无需修改: {json_path}", level="info")
            except Exception as e:
                self.log(f"修正 {json_path} 失败: {str(e)}", level="error")
        if changed == 0:
            self.log("未发现需要修正的cloudUrlConfig.json", level="warning")
        else:
            self.log(f"共修正 {changed} 个cloudUrlConfig.json", level="success")
