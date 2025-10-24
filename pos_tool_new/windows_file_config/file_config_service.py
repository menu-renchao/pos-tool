import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Optional, List
from pos_tool_new.backend import Backend


# 数据模型类
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


@dataclass
class FileConfigItem:
    """文件配置项"""
    name: str
    file_path: str  # 绝对路径或相对路径
    key_values: List[KeyValueItem]
    enabled: bool = True

    def get_absolute_path(self, select_version: str, base_path: str) -> str:
        """根据选择的版本和基础路径获取绝对路径"""
        return f"{base_path}/{select_version}/tomcat/webapps/{self.file_path}"


class WindowsFileConfigService(Backend):
    """Windows文件配置服务"""

    def __init__(self):
        self.APP_DIR = os.path.dirname(sys.argv[0])
        self.CONFIG_JSON_PATH = os.path.join(self.APP_DIR, 'file_config_items.json')
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


        except Exception as e:

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

            with open(self.CONFIG_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)


        except Exception as e:
            self.log(f"保存配置失败: {str(e)}", "error")

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
            if any(item.name == config_item.name for item in self._config_items):
                return False

            self._config_items.append(config_item)
            self._save_config()

            return True
        except Exception as e:

            return False

    def update_config(self, old_name: str, new_config: FileConfigItem) -> bool:
        """更新配置项"""
        try:
            for i, item in enumerate(self._config_items):
                if item.name == old_name:
                    if old_name != new_config.name:
                        if any(item.name == new_config.name for item in self._config_items):
                            return False

                    self._config_items[i] = new_config
                    self._save_config()

                    return True
            return False
        except Exception as e:

            return False

    def delete_config(self, name: str) -> bool:
        """删除配置项"""
        try:
            for i, item in enumerate(self._config_items):
                if item.name == name:
                    del self._config_items[i]
                    self._save_config()

                    return True
            return False
        except Exception as e:

            return False

    def toggle_config_enabled(self, name: str, enabled: bool) -> bool:
        """启用/禁用配置项"""
        try:
            for item in self._config_items:
                if item.name == name:
                    item.enabled = enabled
                    self._save_config()
                    status = "启用" if enabled else "禁用"

                    return True
            return False
        except Exception as e:

            return False

    def modify_file_content(self, content: str, file_config: FileConfigItem, env: str, select_version: str) -> str:
        """修改文件内容，支持版本选择"""

        if file_config.file_path.endswith('.json'):
            new_content = self._modify_json_content(content, file_config, env)
        elif file_config.file_path.endswith('.properties') or file_config.file_path.endswith('.config'):
            new_content = self._modify_properties_content(content, file_config, env)
        else:
            new_content = self._modify_text_content(content, file_config, env)
        return new_content

    def _modify_json_content(self, content: str, file_config: FileConfigItem, env: str) -> str:
        """修改JSON文件内容"""
        try:
            data = json.loads(content)
            for kv_item in file_config.key_values:
                if not kv_item.key:
                    continue
                target_value = kv_item.get_value_by_env(env)
                if not target_value:
                    continue

                keys = kv_item.key.split('.')
                current = data
                for key in keys[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                if keys[-1] in current:
                    current[keys[-1]] = target_value

            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as e:

            return content

    def _modify_properties_content(self, content: str, file_config: FileConfigItem, env: str) -> str:
        """修改Properties文件内容"""
        lines = content.splitlines()
        new_lines = []
        modified_keys = set()

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                new_lines.append(line)
                continue

            key_match = re.match(r'^([^=]+)=.*', line_stripped)
            if key_match:
                key = key_match.group(1).strip()
                for kv_item in file_config.key_values:
                    if kv_item.key == key:
                        target_value = kv_item.get_value_by_env(env)
                        if target_value is not None:
                            new_lines.append(f"{key} = {target_value}")
                            modified_keys.add(key)
                        break
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        for kv_item in file_config.key_values:
            if kv_item.key not in modified_keys:
                target_value = kv_item.get_value_by_env(env)
                if target_value is not None:
                    new_lines.append(f"{kv_item.key} = {target_value}")

        return '\n'.join(new_lines)

    def _modify_text_content(self, content: str, file_config: FileConfigItem, env: str) -> str:
        """修改普通文本文件内容"""
        for kv_item in file_config.key_values:
            if not kv_item.key:
                continue
            target_value = kv_item.get_value_by_env(env)
            if target_value:
                pattern = rf'{re.escape(kv_item.key)}\s*[:=]\s*[^\n\r]*'
                replacement = f'{kv_item.key}: {target_value}'
                content = re.sub(pattern, replacement, content)
        return content


