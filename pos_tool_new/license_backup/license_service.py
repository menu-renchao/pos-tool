import os
from datetime import datetime
from pathlib import Path
from typing import Tuple

import pymysql  # 将 mysql.connector 替换为 pymysql

from pos_tool_new.backend import Backend
from pos_tool_new.utils.db_utils import get_mysql_connection  # 新增导入


class LicenseService(Backend):
    """数据库服务类，处理License备份和恢复的核心逻辑"""

    def __init__(self):
        super().__init__()
        self.strDBpath = "C:\\backup\\"
        self.uname = "shohoku"
        self.uname1 = "root"
        self.upass = "N0mur@4$99!"
        self.dbname = "kpos"
        self.host = ""
        self.uport = "22108"
        self.mid = ""

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
                database=self.dbname,
                user=self.uname,
                password=self.upass,
                port=int(self.uport),
                charset='utf8'
            )

            cursor = connection.cursor()
            cursor.execute(
                "SELECT address1, name, merchant_id, serial_no, "
                "geo_latitude, geo_longitude, map_api_key FROM company_profile"
            )

            result = cursor.fetchone()
            if result:
                self.mid = result[2]  # merchant_id
                self.host = host
                connection.close()
                return True, f"店名:{result[1]} 后台连接成功!"

            connection.close()
            return False, "未找到商户信息"

        except Exception as e:
            return False, f"POS 不在线，或输入IP地址有误！错误: {str(e)}"

    def get_connection(self, host: str):  # 返回类型注释可省略
        """获取数据库连接"""
        try:
            connection = get_mysql_connection(
                host=host,
                database=self.dbname,
                user=self.uname,
                password=self.upass,
                port=int(self.uport),
                charset='utf8'
            )
            return connection
        except Exception as e:
            raise Exception(f"数据库连接失败: {str(e)}")

    def backup_company_profile(self, host: str) -> str:
        """
        备份company_profile表数据，生成格式化的SQL
        """
        connection = self.get_connection(host)
        cursor = connection.cursor(pymysql.cursors.DictCursor)  # 修改为 pymysql 的 DictCursor

        try:
            query = """
                SELECT name, address1, address2, city, state, zipcode, telephone1, telephone2, 
                license_key, merchant_id, merchant_group_id, license_status, timezone, 
                license_expires_on, mode, serial_no 
                FROM company_profile
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            sql_content = "-- ==================== COMPANY_PROFILE 更新 ====================\n\n"

            for row in rows:
                # 使用统一的辅助方法
                name = self._get_string_value(row, 'name')
                address1 = self._get_string_value(row, 'address1')
                address2 = self._get_string_value(row, 'address2')
                city = self._get_string_value(row, 'city')
                state = self._get_string_value(row, 'state')
                zipcode = self._get_string_value(row, 'zipcode')
                telephone1 = self._get_string_value(row, 'telephone1')
                telephone2 = self._get_string_value(row, 'telephone2')
                license_key = self._get_string_value(row, 'license_key')
                merchant_id = self._get_string_value(row, 'merchant_id')
                merchant_group_id = self._get_string_value(row, 'merchant_group_id')
                license_status = self._get_int_value(row, 'license_status')
                timezone = self._get_string_value(row, 'timezone')
                license_expires_on = self._get_string_value(row, 'license_expires_on')
                mode = self._get_string_value(row, 'mode')
                serial_no = self._get_string_value(row, 'serial_no')

                # 构建格式化的UPDATE语句
                update_sql = f"""UPDATE company_profile SET 
        name = {name},
        address1 = {address1},
        address2 = {address2},
        city = {city},
        state = {state},
        zipcode = {zipcode},
        telephone1 = {telephone1},
        telephone2 = {telephone2},
        license_key = {license_key},
        merchant_id = {merchant_id},
        merchant_group_id = {merchant_group_id},
        license_status = {license_status},
        timezone = {timezone},
        license_expires_on = {license_expires_on},
        mode = {mode},
        serial_no = {serial_no};
    """

                sql_content += update_sql + "\n"

            return sql_content

        finally:
            cursor.close()
            connection.close()

    def backup_system_configuration(self, host: str) -> str:
        """备份system_configuration表数据，生成格式化的SQL"""
        connection = self.get_connection(host)
        cursor = connection.cursor(pymysql.cursors.DictCursor)  # 修改为 pymysql 的 DictCursor

        try:
            # 构建DELETE语句
            delete_statements = [
                "-- ==================== SYSTEM_CONFIGURATION 清理 ====================\n",
                "DELETE FROM `kpos`.`system_configuration` WHERE `name` = 'LICENSE_HARDWARE_SIGNATURE_REQUIRED';",
                "DELETE FROM `kpos`.`system_configuration` WHERE `name` = 'MAX_POS_ALLOWED';",
                "DELETE FROM `kpos`.`system_configuration` WHERE `name` = 'MENUSIFU_API_SERVICE_API_KEY';",
                "DELETE FROM `kpos`.`system_configuration` WHERE `name` = 'MENUSIFU_SERVICE_KEY';\n"
            ]

            sql_content = "\n".join(delete_statements)

            # 查询数据
            query = """
                SELECT `name`, `val`, `boolean_val`, `int_val`, `double_val`, `date_val`, `description`, 
                `created_on`, `last_updated`, `created_by`, `last_updated_by`, `version`, `display_name`, 
                `category`, `second_level_category`, `frontend_readable`, `frontend_editable`, `admin_readable`, 
                `admin_editable`, `config_type`, `global_setting`, `user_setting`, `app_setting`, `sync_to_cloud`, 
                `merchant_id`, `sequence_num` 
                FROM system_configuration 
                WHERE `name` in ('LICENSE_HARDWARE_SIGNATURE_REQUIRED','MAX_POS_ALLOWED','MENUSIFU_API_SERVICE_API_KEY','MENUSIFU_SERVICE_KEY')
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            if rows:
                sql_content += "-- ==================== SYSTEM_CONFIGURATION 插入 ====================\n\n"

            for row in rows:
                # 使用统一的辅助方法
                name = self._get_string_value(row, 'name')
                val = self._get_string_value(row, 'val')
                boolean_val = self._get_int_value(row, 'boolean_val')
                int_val = self._get_int_value(row, 'int_val')
                double_val = self._get_double_value(row, 'double_val')
                date_val = self._get_datetime_value(row, 'date_val')
                description = self._get_string_value(row, 'description')
                created_on = self._get_datetime_value(row, 'created_on')
                last_updated = self._get_datetime_value(row, 'last_updated')
                created_by = self._get_int_value(row, 'created_by')
                last_updated_by = self._get_int_value(row, 'last_updated_by')
                version = self._get_int_value(row, 'version')
                display_name = self._get_string_value(row, 'display_name')
                category = self._get_string_value(row, 'category')
                second_level_category = self._get_string_value(row, 'second_level_category')
                frontend_readable = self._get_int_value(row, 'frontend_readable')
                frontend_editable = self._get_int_value(row, 'frontend_editable')
                admin_readable = self._get_int_value(row, 'admin_readable')
                admin_editable = self._get_int_value(row, 'admin_editable')
                config_type = self._get_string_value(row, 'config_type')
                global_setting = self._get_int_value(row, 'global_setting')
                user_setting = self._get_int_value(row, 'user_setting')
                app_setting = self._get_int_value(row, 'app_setting')
                sync_to_cloud = self._get_int_value(row, 'sync_to_cloud')
                merchant_id = self._get_int_value(row, 'merchant_id')
                sequence_num = self._get_int_value(row, 'sequence_num')

                # 构建格式化的INSERT语句
                insert_sql = f"""INSERT INTO system_configuration (
        `name`, `val`, `boolean_val`, `int_val`, `double_val`, `date_val`,
        `description`, `created_on`, `last_updated`, `created_by`, `last_updated_by`,
        `version`, `display_name`, `category`, `second_level_category`,
        `frontend_readable`, `frontend_editable`, `admin_readable`, `admin_editable`,
        `config_type`, `global_setting`, `user_setting`, `app_setting`, `sync_to_cloud`,
        `merchant_id`, `sequence_num`
    ) VALUES (
        {name}, {val}, {boolean_val}, {int_val}, {double_val}, {date_val},
        {description}, {created_on}, {last_updated}, {created_by}, {last_updated_by},
        {version}, {display_name}, {category}, {second_level_category},
        {frontend_readable}, {frontend_editable}, {admin_readable}, {admin_editable},
        {config_type}, {global_setting}, {user_setting}, {app_setting}, {sync_to_cloud},
        {merchant_id}, {sequence_num}
    );
    """

                sql_content += insert_sql + "\n"

            # 添加格式化的额外SQL语句
            additional_sql = """
    -- ==================== 额外配置更新 ====================

    UPDATE system_configuration SET val = NULL WHERE name = 'AWS_SQS_QUEUE_INFO';

    UPDATE kpos.system_configuration SET val = 'https://api.menusifu.cn/performance-env' 
    WHERE name IN ('HEARBEAT_SERVICE_URL', 'MENU_SERVICE_URL', 'MERCHANT_SERVICE_URL', 'ORDER_SERVICE_URL');

    UPDATE system_configuration SET val = 'hWppFMrbyV5+J/BsjHcP5UyoiyVYNw83x2mq8UhxnJAUFfKPSuHU8bumw8ma5LI/' 
    WHERE name = 'MENUSIFU_PUBLIC_API_SERVICE_API_KEY';

    DELETE FROM kpos.sync_scheduled_task_his;

    UPDATE kpos.system_configuration SET boolean_val = 1 
    WHERE name = 'ENABLE_MENUSIFU_PUBLIC_API_SERVICE';

    UPDATE kpos.system_configuration SET val = NULL 
    WHERE `name` = 'AWS_SQS_QUEUE_INFO' AND merchant_id IS NULL;
    """

            sql_content += additional_sql
            return sql_content

        finally:
            cursor.close()
            connection.close()

    def backup_license(self, host: str) -> Tuple[bool, str]:
        """
        完整备份License数据，生成格式化的SQL文件
        """
        try:
            # 首先连接数据库获取merchant_id
            connection = self.get_connection(host)
            cursor = connection.cursor(pymysql.cursors.DictCursor)  # 修改为 pymysql 的 DictCursor

            query = "SELECT address1, name, merchant_id, serial_no, geo_latitude, geo_longitude, map_api_key FROM company_profile;"
            cursor.execute(query)
            result = cursor.fetchone()

            if result:
                self.mid = result['merchant_id']
                store_name = result['name']
                success_msg = f"店名: {store_name} 后台连接成功!"
            else:
                raise Exception("未找到公司配置信息")

            cursor.close()
            connection.close()

            # 备份company_profile
            company_profile_sql = self.backup_company_profile(host)

            # 备份system_configuration
            system_config_sql = self.backup_system_configuration(host)

            # 合并SQL内容，添加文件头注释
            file_header = f"""-- ============================================================
    -- License 备份文件
    -- 商户ID: {self.mid}
    -- 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    -- 工具版本: License备份恢复工具 v1.0
    -- ============================================================

    """
            combined_sql = file_header + company_profile_sql + "\n" + system_config_sql

            # 保存到文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"License{self.mid}_{timestamp}.sql"
            file_path = os.path.join(self.strDBpath, filename)

            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(combined_sql)

            success_msg += f"\nLicense备份成功！路径: {os.path.abspath(file_path)}"
            return True, success_msg

        except Exception as e:
            error_msg = f"导出License不成功: {str(e)}"
            self.log(error_msg)
            return False, error_msg

    def _get_string_value(self, row: dict, key: str) -> str:
        """获取字符串值，正确处理NULL情况"""
        if key in row and row[key] is not None:
            # 正确的转义方式：只需要转义单引号，不要转义双引号
            escaped_value = str(row[key]).replace("'", "''")
            return f"'{escaped_value}'"
        return "null"

    def _get_int_value(self, row: dict, key: str) -> str:
        """获取整数值，正确处理NULL情况"""
        if key in row and row[key] is not None:
            return str(row[key])
        return "null"

    def _get_double_value(self, row: dict, key: str) -> str:
        """获取浮点数值，正确处理NULL情况"""
        if key in row and row[key] is not None:
            return str(row[key])
        return "null"

    def _get_datetime_value(self, row: dict, key: str, default: str = "2020-07-23 13:58:50") -> str:
        """获取日期时间值，处理NULL情况"""
        if key in row and row[key] is not None:
            if isinstance(row[key], datetime):
                return f"'{row[key].strftime('%Y-%m-%d %H:%M:%S')}'"  # 确保有引号
            elif isinstance(row[key], str):
                # 如果是字符串，确保格式正确并添加引号
                return f"'{row[key]}'"
            else:
                # 其他类型转换为字符串并添加引号
                return f"'{str(row[key])}'"
        return f"'{default}'"  # 默认值需要加引号

    def restore_license(self, host: str, file_path: str) -> Tuple[bool, str]:
        """
        恢复License数据（带事务支持）
        """
        connection = None
        try:
            # 验证文件路径
            if not Path(file_path).is_file():
                return False, f"SQL文件不存在: {file_path}"

            # 连接数据库
            connection = pymysql.connect(  # 修改为 pymysql.connect
                host=host,
                database=self.dbname,
                user=self.uname,
                password=self.upass,
                port=int(self.uport),  # pymysql 的 port 需要是 int 类型
                charset='utf8'
            )

            # 开始事务
            connection.autocommit = False
            cursor = connection.cursor()

            # 读取SQL文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # 分割SQL语句
            sql_commands = []
            current_command = ""
            in_string = False
            string_char = None
            escaped = False

            for char in sql_content:
                if char in ("'", '"') and not escaped:
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif string_char == char:
                        in_string = False
                elif char == ";" and not in_string:
                    sql_commands.append(current_command.strip())
                    current_command = ""
                    continue
                elif char == "\\":
                    escaped = not escaped
                else:
                    escaped = False

                current_command += char

            # 添加最后一个命令（如果有）
            if current_command.strip():
                sql_commands.append(current_command.strip())

            # 执行所有SQL语句（在事务中）
            executed_commands = 0
            for i, command in enumerate(sql_commands, 1):
                try:
                    cursor.execute(command)
                    executed_commands += 1
                except Exception as e:
                    self.log(f"执行SQL失败: {command}\n错误: {str(e)}")
                    raise Exception(f"SQL执行失败: {command}\n错误: {str(e)}")

            # 所有语句执行成功，提交事务
            connection.commit()
            self.log(f"成功执行所有 {executed_commands} 条SQL语句，事务已提交", level="success")
            return True, f"License导入成功！共执行 {executed_commands} 条SQL语句"

        except Exception as e:
            if connection:
                connection.rollback()
            error_msg = f"License恢复失败: {str(e)}"
            self.log(error_msg)
            return False, error_msg

        finally:
            # 确保连接关闭
            if connection and connection.open:  # 修改为 connection.open 检查连接状态
                connection.close()

    def expand_app_license(self, host: str) -> tuple:
        """
        扩充app license，批量更新 system_configuration 表相关字段。
        """
        sqls = [
            "UPDATE `kpos`.`system_configuration` SET `val` = 'p7U2ZUeN6xKXDXk566n7o5LW7xgU9mJKokLkPSRLY/b+keGOkn5QWBX0OOBHRG94' WHERE `name` = 'MAX_ANDROID_PHONE_ALLOWED';",
            "UPDATE `kpos`.`system_configuration` SET `val` = 'GDy3abGKC4D/9TtUYsKppq4LnHyrTAD2thP2rFyVX8sjsyFCvwBg4a8tAJ0EwjJw' WHERE `name` = 'MAX_ANDROID_TABLET_ALLOWED';",
            "UPDATE `kpos`.`system_configuration` SET `val` = 'GDy3abGKC4D/9TtUYsKpprmrw8UMha3smpFl0c/TKVJtJyQuFyd0d299P6d/3PL7' WHERE `name` = 'MAX_ANDROID_TABLET_PRO_ALLOWED';",
            "UPDATE `kpos`.`system_configuration` SET `val` = 'L/fHcKKq77rxJ2C/yIxNF6Rq1eEi9BVcw/9JNfpsvLY=' WHERE `name` = 'MAX_EMENU_ALLOWED';",
            "UPDATE `kpos`.`system_configuration` SET `val` = 'BxsBtccMz9jC27L/0WCXs+Hz2ApjctPWcB+iwlKfnHY=' WHERE `name` = 'MAX_IPAD_POS_ALLOWED';",
            "UPDATE `kpos`.`system_configuration` SET `val` = 'dYxAvEQSLsApncLAG4skKz799PHP0Ke0yRZShaIp0Pw=' WHERE `name` = 'MAX_IPHONE_POS_ALLOWED';",
            "UPDATE `kpos`.`system_configuration` SET `val` = 'W+Gws/SSiIGtRMrKuBMbm6Rq1eEi9BVcw/9JNfpsvLY=' WHERE `name` = 'MAX_KIOSK_ALLOWED';",
            "UPDATE `kpos`.`system_configuration` SET `val` = 'rseq0eV7k0GutUWOzFKrP8z2Dztwmr4JRJN1eNIj5LusIFWxrvj71FV9EY6cScoi' WHERE `name` = 'MAX_KITCHEN_DISPLAY_ALLOWED';",
            "UPDATE `kpos`.`system_configuration` SET `val` = 'YJRca2DvpxbfcVNq1PeP3ox+W+rVUx3zDuUIhsQS4VY=' WHERE `name` = 'MAX_ONLINE_ORDER_ALLOWED';",
            "UPDATE `kpos`.`system_configuration` SET `val` = '83T2AYYSwUe0gBUpqAd1eQJE02cm8P9hpLyPXvLtZQM=' WHERE `name` = 'MAX_POS_ALLOWED';",
            "UPDATE `kpos`.`system_configuration` SET `val` = 'RhFZNwyT22bG+BLC3A1dRJTXS5M4qr3sqnR9tSVcrU8=' WHERE `name` = 'MAX_POS_ANDROID_ALLOWED';",
            "UPDATE `kpos`.`system_configuration` SET `val` = 's7TKvzzWJijMhGkB9b89jxl4taQd3iQAB8+l3eTyV8A=' WHERE `name` = 'MAX_POS_IOS_ALLOWED';",
            "UPDATE `kpos`.`system_configuration` SET `val` = 'uw9Be0esfL0frC/3KNWfpH/2h56xdqeoEAWizV/GBlHVEgu7U9gPH8EgK2D9bUpQ' WHERE `name` = 'MAX_REGISTER_DISPLAY_ALLOWED';",
            "UPDATE `kpos`.`system_configuration` SET `val` = 'nSVjOTz42iTBvTh++X/YzV/W/4Fm8X/yrERJp0OXjoHX40ZEbvK55e5wJGj6g4vv' WHERE `name` = 'MAX_SELF_SERVICE_TERMINAL_ALLOWED';",
            "UPDATE `kpos`.`system_configuration` SET `val` = 'zFhFfSQP0Rb2iwcHJrcQ8B3g71MXl34TP04JN+HULceWRSS2gxione+EOdHavZDZ' WHERE `name` = 'MAX_WEARABLE_DEVICE_ALLOWED';"
        ]
        try:
            conn = self.get_connection(host)
            cursor = conn.cursor()
            for sql in sqls:
                cursor.execute(sql)
            conn.commit()
            cursor.close()
            conn.close()
            return True, "扩充app license成功！"
        except Exception as e:
            return False, f"扩充app license失败: {str(e)}"
