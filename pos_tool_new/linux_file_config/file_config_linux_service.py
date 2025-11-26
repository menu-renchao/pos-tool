import json
import os
import re
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

from pos_tool_new.backend import Backend


@dataclass
class KeyValueItem:
    """键值对配置项"""
    key: str
    qa_value: str = ""
    prod_value: str = ""
    dev_value: str = ""

    def get_value_by_env(self, env: str) -> str:
        """根据环境获取对应的值"""
        env = env.upper()
        if env == "QA":
            return self.qa_value
        elif env == "PROD":
            return self.prod_value
        elif env == "DEV":
            return self.dev_value
        return ""

    def set_value_by_env(self, env: str, value: str):
        """根据环境设置对应的值"""
        env = env.upper()
        if env == "QA":
            self.qa_value = value
        elif env == "PROD":
            self.prod_value = value
        elif env == "DEV":
            self.prod_value = value


@dataclass
class FileConfigItem:
    """文件配置项"""
    name: str
    file_path: str  # 相对路径，如 "kpos/front/js/cloudUrlConfig.json"
    key_values: List[KeyValueItem]
    enabled: bool = True

    def get_absolute_path(self) -> str:
        """获取绝对路径"""
        return f"/opt/tomcat7/webapps/{self.file_path}"


class FileConfigService(Backend):
    """文件配置服务"""

    def __init__(self):
        super().__init__()
        self.APP_DIR = os.path.dirname(sys.argv[0])
        self.CONFIG_JSON_PATH = os.path.join(self.APP_DIR, 'file_config.json')
        self._config_items: List[FileConfigItem] = []
        self._load_config()

    def _load_config(self):
        """从JSON文件加载配置"""
        try:
            if not os.path.exists(self.CONFIG_JSON_PATH):
                self._config_items = []
                self._save_config()
                return

            with open(self.CONFIG_JSON_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._config_items = []
            for item_data in data:
                key_values = []
                for kv_data in item_data.get('key_values', []):
                    key_values.append(KeyValueItem(
                        key=kv_data.get('key', ''),
                        qa_value=kv_data.get('qa_value', ''),
                        prod_value=kv_data.get('prod_value', ''),
                        dev_value=kv_data.get('dev_value', '')
                    ))

                self._config_items.append(FileConfigItem(
                    name=item_data.get('name', ''),
                    file_path=item_data.get('file_path', ''),
                    key_values=key_values,
                    enabled=item_data.get('enabled', True)
                ))

            self.log(f"加载文件配置项: {len(self._config_items)} 个", level="info")
        except Exception as e:
            self.log(f"加载配置文件失败: {str(e)}", level="error")
            self._config_items = []

    def _save_config(self):
        """保存配置到JSON文件"""
        try:
            data = []
            for item in self._config_items:
                item_data = {
                    'name': item.name,
                    'file_path': item.file_path,
                    'enabled': item.enabled,
                    'key_values': []
                }
                for kv in item.key_values:
                    item_data['key_values'].append({
                        'key': kv.key,
                        'qa_value': kv.qa_value,
                        'prod_value': kv.prod_value,
                        'dev_value': kv.dev_value
                    })
                data.append(item_data)

            # 记录保存前后的摘要日志（完整内容，不截断）
            self.log(f"准备保存文件配置到: {self.CONFIG_JSON_PATH}", level="info")
            self.log(f"保存内容摘要: {json.dumps(data, ensure_ascii=False)}", level="debug")

            with open(self.CONFIG_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.log("文件配置已保存", level="info")
        except Exception as e:
            self.log(f"保存配置文件失败: {str(e)}", level="error")

    def get_all_configs(self) -> List[FileConfigItem]:
        """获取所有配置项"""
        return self._config_items.copy()

    def get_config_by_name(self, name: str) -> Optional[FileConfigItem]:
        """根据名称获取配置项"""
        for item in self._config_items:
            if item.name == name:
                return item
        return None

    def add_config(self, config_item: FileConfigItem) -> bool:
        """添加配置项"""
        try:
            # 检查名称是否重复
            if any(item.name == config_item.name for item in self._config_items):
                return False

            self._config_items.append(config_item)
            self._save_config()
            self.log(f"添加文件配置项: {config_item.name}", level="info")
            return True
        except Exception as e:
            self.log(f"添加配置项失败: {str(e)}", level="error")
            return False

    def update_config(self, old_name: str, new_config: FileConfigItem) -> bool:
        """
        更新配置项，记录详细差异日志
        """
        try:
            for i, item in enumerate(self._config_items):
                if item.name == old_name:
                    # 如果名称改变，检查新名称是否重复
                    if old_name != new_config.name:
                        if any(x.name == new_config.name for x in self._config_items):
                            return False

                    # 记录差异日志
                    changes = []
                    if item.name != new_config.name:
                        changes.append(f"name: '{item.name}' -> '{new_config.name}'")
                    if item.file_path != new_config.file_path:
                        changes.append(f"file_path: '{item.file_path}' -> '{new_config.file_path}'")
                    if item.enabled != new_config.enabled:
                        changes.append(f"enabled: {item.enabled} -> {new_config.enabled}")
                    # 对比 key_values
                    old_keys = {kv.key: kv for kv in item.key_values}
                    new_keys = {kv.key: kv for kv in new_config.key_values}
                    for key in old_keys:
                        if key not in new_keys:
                            changes.append(f"删除键: {key}")
                        else:
                            old_kv, new_kv = old_keys[key], new_keys[key]
                            for env in ["QA", "PROD", "DEV"]:
                                old_val = old_kv.get_value_by_env(env)
                                new_val = new_kv.get_value_by_env(env)
                                if old_val != new_val:
                                    changes.append(f"{key} [{env}]: '{old_val}' -> '{new_val}'")
                    for key in new_keys:
                        if key not in old_keys:
                            changes.append(
                                f"新增键: {key}，值: QA='{new_keys[key].qa_value}', PROD='{new_keys[key].prod_value}', DEV='{new_keys[key].dev_value}'")
                    if changes:
                        self.log(f"更新文件配置项: {old_name} -> {new_config.name}，变更: " + "; ".join(changes),
                                 level="info")
                    else:
                        self.log(f"更新文件配置项: {old_name} -> {new_config.name}，无字段变更", level="info")

                    self._config_items[i] = new_config
                    self._save_config()
                    return True
            return False
        except Exception as e:
            self.log(f"更新配置项失败: {str(e)}", level="error")
            return False

    def delete_config(self, name: str) -> bool:
        """删除配置项"""
        try:
            for i, item in enumerate(self._config_items):
                if item.name == name:
                    del self._config_items[i]
                    self._save_config()
                    self.log(f"删除文件配置项: {name}", level="info")
                    return True
            return False
        except Exception as e:
            self.log(f"删除配置项失败: {str(e)}", level="error")
            return False

    def toggle_config_enabled(self, name: str, enabled: bool) -> bool:
        """启用/禁用配置项"""
        try:
            for item in self._config_items:
                if item.name == name:
                    item.enabled = enabled
                    self._save_config()
                    status = "启用" if enabled else "禁用"
                    self.log(f"{status}文件配置项: {name}", level="info")
                    return True
            return False
        except Exception as e:
            self.log(f"切换配置项状态失败: {str(e)}", level="error")
            return False

    def modify_remote_file_content(self, content: str, file_config: FileConfigItem, env: str) -> str:
        """修改远程文件内容"""
        try:
            self.log(f"开始修改远程文件内容: {file_config.file_path}, 环境: {env}", level="info")
            self.log(f"原始内容摘要: {content[:500]}", level="debug")
            # 根据文件类型采用不同的修改策略
            if file_config.file_path.endswith('.json'):
                new_content = self._modify_json_content(content, file_config, env)
            elif file_config.file_path.endswith('.properties'):
                new_content = self._modify_properties_content(content, file_config, env)
            else:
                # 默认使用文本替换
                new_content = self._modify_text_content(content, file_config, env)
            self.log(f"修改后内容摘要: {new_content[:500]}", level="debug")
            return new_content
        except Exception as e:
            self.log(f"修改文件内容失败: {str(e)}", level="error")
            return content

    def _modify_json_content(self, content: str, file_config: FileConfigItem, env: str) -> str:
        """修改JSON文件内容"""
        try:
            import json as json_lib
            data = json_lib.loads(content)
            before = json_lib.dumps(data, ensure_ascii=False)[:500]
            for kv_item in file_config.key_values:
                if not kv_item.key:
                    continue
                target_value = kv_item.get_value_by_env(env)
                if not target_value:
                    continue
                # 支持嵌套键路径，如 "a.b.c"
                keys = kv_item.key.split('.')
                current = data
                for key in keys[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                if keys[-1] in current:
                    current[keys[-1]] = target_value
                else:
                    self.log(f"未找到字段: {kv_item.key}", level="warning")
            after = json_lib.dumps(data, ensure_ascii=False)[:500]
            self.log(f"JSON内容修改前摘要: {before}", level="debug")
            self.log(f"JSON内容修改后摘要: {after}", level="debug")
            return json_lib.dumps(data, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"修改JSON内容失败: {str(e)}", level="error")
            return content

    def _modify_properties_content(self, content: str, file_config: FileConfigItem, env: str) -> str:
        """修改Properties文件内容"""
        before = content[:500]
        lines = content.splitlines()
        new_lines = []
        modified_keys = set()
        # 先处理现有行
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                new_lines.append(line)
                continue
            key_match = re.match(r'^([^=]+)=.*', line_stripped)
            if key_match:
                key = key_match.group(1).strip()
                found = False
                for kv_item in file_config.key_values:
                    if kv_item.key == key:
                        target_value = kv_item.get_value_by_env(env)
                        if target_value is not None:
                            new_lines.append(f"{key} = {target_value}")
                            modified_keys.add(key)
                        found = True
                        break
                if not found:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        # 添加未存在的新键值
        for kv_item in file_config.key_values:
            if kv_item.key not in modified_keys:
                target_value = kv_item.get_value_by_env(env)
                if target_value is not None:
                    new_lines.append(f"{kv_item.key} = {target_value}")
                    self.log(f"未找到字段: {kv_item.key}", level="warning")
        after = '\n'.join(new_lines)[:500]
        self.log(f"Properties内容修改前摘要: {before}", level="debug")
        self.log(f"Properties内容修改后摘要: {after}", level="debug")
        return '\n'.join(new_lines)

    def _modify_text_content(self, content: str, file_config: FileConfigItem, env: str) -> str:
        """修改普通文本文件内容"""
        before = content[:500]
        modified_keys = set()
        result = content
        for kv_item in file_config.key_values:
            if not kv_item.key:
                continue
            target_value = kv_item.get_value_by_env(env)
            if target_value:
                if kv_item.key in content:
                    result = result.replace(kv_item.key, target_value)
                    modified_keys.add(kv_item.key)
                else:
                    self.log(f"未找到字段: {kv_item.key}", level="warning")
        after = result[:500]
        self.log(f"文本内容修改前摘要: {before}", level="debug")
        self.log(f"文本内容修改后摘要: {after}", level="debug")
        return result

    def execute_config_modification(self, host: str, username: str, password: str,
                                    file_config: FileConfigItem, env: str) -> Tuple[bool, str]:
        """执行配置文件修改"""
        try:
            from pos_tool_new.linux_pos.linux_service import LinuxService
            linux_service = LinuxService()
            ssh = linux_service._connect_ssh(host, username, password)
            remote_path = file_config.get_absolute_path()
            self.log(f"远程主机: {host}, 文件路径: {remote_path}", level="info")

            if not linux_service._check_file_exists(ssh, remote_path):
                self.log(f"远程文件不存在: {remote_path}", level="error")
                return False, f"远程文件不存在: {remote_path}"

            content = linux_service._read_remote_file(ssh, remote_path)
            self.log(f"远程文件原始内容摘要: {content[:500]}", level="debug")

            new_content = self.modify_remote_file_content(content, file_config, env)
            self.log(f"远程文件修改后内容摘要: {new_content[:500]}", level="debug")
            if remote_path.lower().endswith('.json'):
                import json
                try:
                    if json.loads(content) == json.loads(new_content):
                        self.log(f"文件内容无需修改: {remote_path}", level="info")
                        ssh.close()
                        return True, "文件内容无需修改"
                except Exception:
                    pass  # 如果解析失败则回退到原始比较
            if content == new_content:
                self.log(f"文件内容无需修改: {remote_path}", level="info")
                ssh.close()
                return True, "文件内容无需修改"

            linux_service._write_remote_file(ssh, remote_path, new_content)
            self.log(f"文件已写入新内容: {remote_path}", level="info")
            ssh.close()
            return True, f"文件修改成功: {remote_path}"
        except Exception as e:
            self.log(f"修改文件失败: {str(e)}", level="error")
            return False, f"修改文件失败: {str(e)}"
