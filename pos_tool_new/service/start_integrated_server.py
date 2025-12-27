#!/usr/bin/env python3
"""
集成服务器启动脚本
运行命令: python start_integrated_server.py
"""

import asyncio
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main_server import main

if __name__ == "__main__":
    print("=" * 50)
    print("集成服务器启动中...")
    print("服务列表:")
    print("1. WebSocket聊天服务器 (端口: 56789)")
    print("2. HTTP API服务器 (端口: 5001)")
    print("3. 版本管理服务 (/api/version, /api/download)")
    print("4. 短信接收服务 (/api/usable_phone_numbers, /api/latest_code)")
    print("=" * 50)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n服务器正在关闭...")
    except Exception as e:
        print(f"服务器启动失败: {e}")