import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from pos_tool_new.backend import Backend


@dataclass
class JacocoActionResult:
    success: bool
    message: str
    data: dict | None = None


class WindowsService(Backend):
    JACOCO_AGENT_MARKER = "jacocoagent.jar"
    JACOCO_REPORT_SCRIPT = "buildReport.bat"
    JACOCO_BACKUP_SUFFIX = ".jacoco.bak"

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

    def stop_pos_windows(self):
        """结束 Windows 下的 POS 进程"""
        try:
            os.system('taskkill /IM "Menusifu POS.exe" /T /F')
            self.log("POS 进程已结束！", level="success")
        except Exception as e:
            self.log(f"结束 POS 进程出错: {str(e)}", level="error")

    def start_pos_windows(self, base_path, selected_version):
        """启动 Windows 下的 POS 应用"""
        try:
            version_path = os.path.join(base_path, selected_version)
            pos_exe_path = os.path.join(version_path, r"Menusifu Server Manager\Menusifu POS.exe")
            os.startfile(pos_exe_path)
            self.log(f"{selected_version} POS 启动成功！", level="success")
        except Exception as e:
            self.log(f"启动 POS 出错: {str(e)}", level="error")

    def restart_pos_windows(self, base_path, selected_version):
        """重启 Windows 下的 POS 应用"""
        try:
            self.stop_pos_windows()
            self.start_pos_windows(base_path, selected_version)
            self.log(f"{selected_version} POS 重启成功！", level="success")
        except Exception as e:
            self.log(f"重启 POS 出错: {str(e)}", level="error")

    def get_version_path(self, base_path, selected_version):
        return Path(base_path) / selected_version

    def get_setenv_path(self, version_path):
        return Path(version_path) / "tomcat" / "bin" / "setenv.bat"

    def get_jacoco_backup_path(self, setenv_path):
        return Path(f"{setenv_path}{self.JACOCO_BACKUP_SUFFIX}")

    def get_jacoco_dirs(self, version_path):
        version_dir = Path(version_path)
        if not version_dir.exists():
            return []
        return sorted(
            [path for path in version_dir.iterdir() if path.is_dir() and path.name.lower().startswith("jacoco-")],
            reverse=True,
        )

    def has_jacoco_agent(self, content):
        return self.JACOCO_AGENT_MARKER in content

    def deploy_jacoco(self, base_path, selected_version, zip_path):
        version_path = self.get_version_path(base_path, selected_version)
        setenv_path = self.get_setenv_path(version_path)
        archive_path = Path(zip_path)

        if not version_path.is_dir():
            return JacocoActionResult(False, f"版本目录不存在: {version_path}")
        if not archive_path.is_file():
            return JacocoActionResult(False, f"JaCoCo 压缩包不存在: {archive_path}")
        if not setenv_path.is_file():
            return JacocoActionResult(False, f"setenv.bat 不存在: {setenv_path}")

        jacoco_root = self.extract_jacoco_zip(archive_path, version_path)
        if not jacoco_root:
            return JacocoActionResult(False, "JaCoCo 压缩包中未找到有效目录")

        backup_path = self.get_jacoco_backup_path(setenv_path)
        if not backup_path.exists():
            shutil.copy2(setenv_path, backup_path)
            self.log(f"已备份 setenv.bat: {backup_path}", level="info")

        content = setenv_path.read_text(encoding="utf-8")
        if self.has_jacoco_agent(content):
            self.log("JaCoCo 已部署，跳过重复注入", level="warning")
        else:
            updated_content = self.inject_jacoco_agent(content, jacoco_root)
            setenv_path.write_text(updated_content, encoding="utf-8")
            self.log(f"已写入 JaCoCo agent 配置: {setenv_path}", level="success")

        report_script_path = jacoco_root / "lib" / self.JACOCO_REPORT_SCRIPT
        report_script_path.parent.mkdir(parents=True, exist_ok=True)
        report_script_path.write_text(
            self.build_report_script_content(version_path, jacoco_root),
            encoding="utf-8",
        )
        self.log(f"已生成覆盖率脚本: {report_script_path}", level="success")
        return JacocoActionResult(
            True,
            "JaCoCo 部署完成，请重启 POS 后执行用例再生成覆盖率报告",
            {"jacoco_root": str(jacoco_root), "report_script": str(report_script_path)},
        )

    def restore_jacoco(self, base_path, selected_version):
        version_path = self.get_version_path(base_path, selected_version)
        setenv_path = self.get_setenv_path(version_path)
        backup_path = self.get_jacoco_backup_path(setenv_path)

        if not version_path.is_dir():
            return JacocoActionResult(False, f"版本目录不存在: {version_path}")
        if not backup_path.is_file():
            return JacocoActionResult(False, f"未找到 JaCoCo 备份文件: {backup_path}")

        shutil.copy2(backup_path, setenv_path)
        self.log(f"已恢复 setenv.bat: {setenv_path}", level="success")

        removed_scripts = []
        for jacoco_dir in self.get_jacoco_dirs(version_path):
            report_script = jacoco_dir / "lib" / self.JACOCO_REPORT_SCRIPT
            if report_script.exists():
                report_script.unlink()
                removed_scripts.append(str(report_script))

        message = "JaCoCo 恢复完成"
        if removed_scripts:
            message += f"，已删除 {len(removed_scripts)} 个报告脚本"
        return JacocoActionResult(True, message, {"removed_scripts": removed_scripts})

    def validate_jacoco_report_requirements(self, version_path, jacoco_root):
        version_dir = Path(version_path)
        jacoco_dir = Path(jacoco_root)
        checks = {
            "java.exe": version_dir / "jre" / "bin" / "java.exe",
            "jacococli.jar": jacoco_dir / "lib" / "jacococli.jar",
            "WEB-INF\\classes": version_dir / "tomcat" / "webapps" / "kpos" / "WEB-INF" / "classes",
            self.JACOCO_REPORT_SCRIPT: jacoco_dir / "lib" / self.JACOCO_REPORT_SCRIPT,
        }
        missing = [name for name, path in checks.items() if not path.exists()]
        if missing:
            return JacocoActionResult(False, f"缺少运行覆盖率报告所需文件: {', '.join(missing)}")
        return JacocoActionResult(True, "JaCoCo 报告依赖校验通过", {"paths": {k: str(v) for k, v in checks.items()}})

    def generate_jacoco_report(self, base_path, selected_version):
        version_path = self.get_version_path(base_path, selected_version)
        jacoco_dirs = self.get_jacoco_dirs(version_path)
        if not jacoco_dirs:
            return JacocoActionResult(False, f"未找到 JaCoCo 目录: {version_path}")

        jacoco_root = jacoco_dirs[0]
        validation = self.validate_jacoco_report_requirements(version_path, jacoco_root)
        if not validation.success:
            return validation

        report_script = jacoco_root / "lib" / self.JACOCO_REPORT_SCRIPT
        process = subprocess.run(
            ["cmd", "/c", str(report_script), "--no-open", "--no-pause"],
            cwd=report_script.parent,
            capture_output=True,
            text=True,
            check=False,
        )
        if process.returncode != 0:
            stderr = process.stderr.strip() or process.stdout.strip() or "未知错误"
            return JacocoActionResult(False, f"生成覆盖率报告失败: {stderr}")

        report_index = jacoco_root / "lib" / "jacocoreport" / "index.html"
        if not report_index.exists():
            return JacocoActionResult(False, f"覆盖率报告未生成: {report_index}")

        os.startfile(str(report_index))
        return JacocoActionResult(True, f"覆盖率报告已生成: {report_index}", {"report_index": str(report_index)})

    def extract_jacoco_zip(self, archive_path, version_path):
        with zipfile.ZipFile(archive_path, "r") as archive:
            roots = []
            has_top_level_lib = False
            for name in archive.namelist():
                normalized = name.strip("/\\")
                if not normalized:
                    continue
                root = normalized.split("/", 1)[0].split("\\", 1)[0]
                if root.lower().startswith("jacoco-"):
                    roots.append(root)
                if normalized.lower().startswith("lib/") or normalized.lower().startswith("lib\\"):
                    has_top_level_lib = True

            if roots:
                archive.extractall(version_path)
                return Path(version_path) / sorted(set(roots))[0]

            target_root = Path(version_path) / Path(archive_path).stem
            if has_top_level_lib and target_root.name.lower().startswith("jacoco-"):
                target_root.mkdir(parents=True, exist_ok=True)
                archive.extractall(target_root)
                return target_root

            return None

    def inject_jacoco_agent(self, content, jacoco_root):
        agent_path = (Path(jacoco_root) / "lib" / "jacocoagent.jar").as_posix()
        agent_line = (
            f"set JAVA_OPTS=%JAVA_OPTS%  -javaagent:{agent_path}"
            "=includes=com.wisdomount.*,output=tcpserver,port=9527,address=127.0.0.1,append=true -Xverify:none"
        )
        lines = content.splitlines(keepends=True)
        for index, line in enumerate(lines):
            if line.strip().lower().startswith("set java_opts"):
                lines.insert(index + 1, agent_line + "\n")
                return "".join(lines)

        suffix = "" if content.endswith(("\n", "\r")) else "\n"
        return content + suffix + ":: JaCoCo agent configuration\n" + agent_line + "\n"

    def build_report_script_content(self, version_path, jacoco_root):
        version_dir = Path(version_path)
        jacoco_dir = Path(jacoco_root)
        jre_home = self._to_windows_path(version_dir / "jre")
        tomcat_home = self._to_windows_path(version_dir / "tomcat")
        jacoco_lib = self._to_windows_path(jacoco_dir / "lib")
        return (
            "@echo off\n"
            "setlocal enabledelayedexpansion\n\n"
            ":: ============== Environment Variables ==============\n"
            f'set "JRE_HOME={jre_home}"\n'
            f'set "TOMCAT_HOME={tomcat_home}"\n'
            f'set "JACOCO_LIB={jacoco_lib}"\n'
            'set "REPORT_DIR=%JACOCO_LIB%\\jacocoreport"\n'
            'set "PORT=9527"\n'
            'set "ADDRESS=127.0.0.1"\n\n'
            'set "NO_OPEN=0"\n'
            'set "NO_PAUSE=0"\n'
            'if /I "%~1"=="--no-open" set "NO_OPEN=1"\n'
            'if /I "%~1"=="--no-pause" set "NO_PAUSE=1"\n'
            'if /I "%~2"=="--no-open" set "NO_OPEN=1"\n'
            'if /I "%~2"=="--no-pause" set "NO_PAUSE=1"\n\n'
            ":: ============== Clean Report Directory ==============\n"
            'if exist "%REPORT_DIR%" (\n'
            '    echo [INFO] Deleting directory: %REPORT_DIR%\n'
            '    rd /s /q "%REPORT_DIR%" >nul 2>&1\n'
            '    timeout /t 2 >nul\n'
            '    if exist "%REPORT_DIR%" (\n'
            '        echo [ERROR] Failed to delete directory. Check permissions or file locks.\n'
            '        if "%NO_PAUSE%"=="0" pause\n'
            '        exit /b 1\n'
            '    )\n'
            ') else (\n'
            '    echo [INFO] Directory does not exist: %REPORT_DIR%\n'
            ')\n'
            'if not exist "%REPORT_DIR%" mkdir "%REPORT_DIR%"\n'
            ":: ============== TCP Dump ==============\n"
            'echo [INFO] Dumping coverage data from %ADDRESS%:%PORT%...\n'
            '"%JRE_HOME%\\bin\\java" -jar "%JACOCO_LIB%\\jacococli.jar" dump ^\n'
            '    --address %ADDRESS% --port %PORT% ^\n'
            '    --destfile "%REPORT_DIR%\\jacoco.exec"\n'
            "if errorlevel 1 (\n"
            '    echo [ERROR] Failed to get coverage data. Check if TCP service is running.\n'
            '    if "%NO_PAUSE%"=="0" pause\n'
            '    exit /b 1\n'
            ')\n\n'
            ":: ============== Generate HTML Report ==============\n"
            'echo [INFO] Generating HTML report in %REPORT_DIR%...\n'
            '"%JRE_HOME%\\bin\\java" -jar "%JACOCO_LIB%\\jacococli.jar" report ^\n'
            '    "%REPORT_DIR%\\jacoco.exec" ^\n'
            '    --classfiles "%TOMCAT_HOME%\\webapps\\kpos\\WEB-INF\\classes" ^\n'
            '    --html "%REPORT_DIR%"\n'
            "if errorlevel 1 (\n"
            '    echo [ERROR] Report generation failed. Check file paths.\n'
            '    if "%NO_PAUSE%"=="0" pause\n'
            '    exit /b 1\n'
            ')\n\n'
            ":: ============== Display Result ==============\n"
            'echo [SUCCESS] Report generated: %REPORT_DIR%\\index.html\n'
            'if "%NO_OPEN%"=="0" start "" "%REPORT_DIR%\\index.html"\n'
            'if "%NO_PAUSE%"=="0" pause\n'
        )

    @staticmethod
    def _to_windows_path(path):
        return str(Path(path)).replace("/", "\\")

    # 效期管理
    def fix_expiration_management_url(self, base_path, env):
        r"""
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
