import json
import os
import sys
from typing import List, Dict, Any, Tuple

from pos_tool_new.backend import Backend
from pos_tool_new.utils.db_utils import get_mysql_connection

APP_DIR = os.path.dirname(sys.argv[0])
CONFIG_JSON_PATH = os.path.join(APP_DIR, 'db_config.json')


class ConfigItem:
    def __init__(self, description: str, sqls: List[str], need_restart: bool):
        self.description = description
        self.sqls = sqls
        self.need_restart = need_restart

    def to_dict(self):
        return {
            'description': self.description,
            'sqls': self.sqls,
            'need_restart': self.need_restart
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        return ConfigItem(
            description=data['description'],
            sqls=data['sqls'],
            need_restart=data['need_restart']
        )


class DbConfigService(Backend):
    """
    数据库配置项服务，负责根据配置项和开关状态生成 SQL 并执行。
    """

    def _load_config_items(self) -> List[ConfigItem]:
        if not os.path.exists(CONFIG_JSON_PATH):
            # 自动新建空配置文件
            with open(CONFIG_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            return []
        with open(CONFIG_JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [ConfigItem.from_dict(item) for item in data]

    def _save_config_items(self, items: List[ConfigItem]):
        with open(CONFIG_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump([item.to_dict() for item in items], f, ensure_ascii=False, indent=2)

    def get_config_items(self) -> List[ConfigItem]:
        return self._load_config_items()

    def add_config_item(self, item: ConfigItem) -> bool:
        items = self._load_config_items()
        if any(i.description == item.description for i in items):
            return False  # 名称唯一性校验失败
        items.append(item)
        self._save_config_items(items)
        return True

    def update_config_item(self, new_item, original_description):
        """
        Update the config item whose description matches original_description with new_item.
        """
        items = self.get_config_items()
        updated = False
        for idx, item in enumerate(items):
            if item.description == original_description:
                items[idx] = new_item
                updated = True
                break
        if updated:
            self._save_config_items(items)
        else:
            raise ValueError(f"Config item with description '{original_description}' not found.")

    def delete_config_item(self, description: str) -> bool:
        items = self._load_config_items()
        new_items = [i for i in items if i.description != description]
        if len(new_items) == len(items):
            return False  # 未找到
        self._save_config_items(new_items)
        return True

    def set_config(self, items: list, db_params: dict) -> dict:
        """
        根据传入的 ConfigItem 列表，批量执行SQL。
        返回每个规则是否需要重启。
        """
        result = {}
        conn = get_mysql_connection(**db_params)
        cursor = conn.cursor()
        for item in items:
            for sql in item.sqls:
                self.log(f"执行SQL: {sql}")
                cursor.execute(sql)
            result[item.description] = item.need_restart
        conn.commit()
        cursor.close()
        conn.close()
        return result

    def connect_database(self, host: str) -> Tuple[bool, str]:
        """
        连接数据库并验证连接
        Args:
            host: 数据库主机地址
        Returns:
            (成功标志, 消息)
        """
        try:
            connection = get_mysql_connection(
                host=host,
                database='kpos',
                user='shohoku',
                password='N0mur@4$99!',
                port=22108,
                charset='utf8'
            )
            cursor = connection.cursor()
            cursor.execute(
                "SELECT address1, name, merchant_id, serial_no, geo_latitude, geo_longitude, map_api_key FROM company_profile"
            )
            result = cursor.fetchone()
            if result:
                connection.close()
                return True, f"店名:{result[1]} 后台连接成功!"
            connection.close()
            return False, "未找到商户信息"
        except Exception as e:
            return False, f"POS 不在线，或输入IP地址有误！错误: {str(e)}"
