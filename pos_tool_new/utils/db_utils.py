import pymysql

from pos_tool_new.utils.log_manager import global_log_manager


def get_mysql_connection(host: str, database: str, user: str, password: str, port: int, charset: str = 'utf8'):
    """
    获取 MySQL 数据库连接
    Args:
        host: 数据库主机地址
        database: 数据库名
        user: 用户名
        password: 密码
        port: 端口号
        charset: 字符集，默认 utf8
    Returns:
        pymysql.connections.Connection
    Raises:
        Exception: 连接失败时抛出异常
    """
    try:

        connection = pymysql.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port,
            charset=charset
        )
        global_log_manager.log(f"成功连接到数据库 {database} 于 {host}:{port} 作为用户 {user}", level="success")
        return connection
    except pymysql.Error as e:
        global_log_manager.log(f"数据库连接失败: {str(e)}", level="error")
        raise Exception(f"数据库连接失败: {str(e)}")
