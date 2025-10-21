from typing import Tuple
from pos_tool_new.backend import Backend
from pos_tool_new.utils.db_utils import get_mysql_connection

class DbConfigService(Backend):
    """
    数据库配置项服务，负责根据配置项和开关状态生成 SQL 并执行。
    """
    # 可扩展配置项映射
    CONFIG_MAP = {
        'Cash discount': 'CASH_DISCOUNT_ENABLE',
        # 可继续添加更多配置项
    }
    def set_config(self, config_name: str, enabled: bool, db_params: dict):
        """
        根据配置项和开关状态，生成 SQL 并执行。
        """
        if config_name not in self.CONFIG_MAP:
            raise ValueError('未知配置项')
        key = self.CONFIG_MAP[config_name]
        value = 1 if enabled else 0
        sql = f"update system_configuration set boolean_val={value} where name='{key}'"
        conn = get_mysql_connection(**db_params)
        cursor = conn.cursor()
        self.log(f"执行SQL: {sql}")
        cursor.execute(sql)
        conn.commit()
        cursor.close()
        conn.close()

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
