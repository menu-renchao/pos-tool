#!/usr/bin/env python3
"""
SQLite Database Viewer
Usage: python db_viewer.py [table_name]
       python db_viewer.py users
       python db_viewer.py mobile_devices
"""

import sqlite3
import sys
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'app.db')


def get_tables(cursor):
    """获取所有表名"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    return [row[0] for row in cursor.fetchall()]


def get_schema(cursor, table):
    """获取表结构"""
    cursor.execute(f"PRAGMA table_info({table});")
    columns = cursor.fetchall()
    print(f"\n表结构: {table}")
    print("-" * 60)
    print(f"{'序号':<6}{'字段名':<20}{'类型':<15}{'非空':<6}{'默认值':<10}")
    print("-" * 60)
    for col in columns:
        cid, name, dtype, notnull, default, pk = col
        print(f"{cid:<6}{name:<20}{dtype:<15}{notnull:<6}{str(default):<10}")


def show_data(cursor, table, limit=20):
    """显示表数据"""
    cursor.execute(f"SELECT * FROM {table} LIMIT {limit};")
    rows = cursor.fetchall()

    if not rows:
        print(f"\n表 {table} 为空")
        return

    # 获取列名
    cursor.execute(f"PRAGMA table_info({table});")
    columns = [col[1] for col in cursor.fetchall()]

    print(f"\n数据: {table} (共 {len(rows)} 条)")
    print("=" * 100)

    # 打印表头
    header = " | ".join(f"{col[:15]:<15}" for col in columns)
    print(header)
    print("-" * len(header))

    # 打印数据
    for row in rows:
        row_str = " | ".join(f"{str(val)[:15]:<15}" if val else "None".ljust(15) for val in row)
        print(row_str)


def main():
    if not os.path.exists(DB_PATH):
        print(f"数据库不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    tables = get_tables(cursor)

    if len(sys.argv) > 1:
        # 查看指定表
        table = sys.argv[1]
        if table in tables:
            get_schema(cursor, table)
            show_data(cursor, table)
        else:
            print(f"表 '{table}' 不存在")
            print(f"可用表: {', '.join(tables)}")
    else:
        # 显示所有表
        print("\n" + "=" * 40)
        print("     POS Scanner 数据库浏览器")
        print("=" * 40)
        print(f"\n数据库: {DB_PATH}")
        print(f"表数量: {len(tables)}")
        print(f"\n可用表:")
        for i, t in enumerate(tables, 1):
            cursor.execute(f"SELECT COUNT(*) FROM {t};")
            count = cursor.fetchone()[0]
            print(f"  {i}. {t} ({count} 条记录)")

        print("\n用法: python db_viewer.py [表名]")
        print("示例: python db_viewer.py users")

    conn.close()


if __name__ == "__main__":
    main()
