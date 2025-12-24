# lan_chat_service.py
import websocket
import threading
import json
import time
import logging
from typing import Callable, Optional

from pos_tool_new.backend import Backend

logger = logging.getLogger(__name__)


class LanChatService(Backend):
    def __init__(self, on_message_callback: Callable, server_url: str = 'ws://localhost:56789'):
        super().__init__()
        self.server_url = server_url
        self.on_message_callback = on_message_callback
        self.nickname = '匿名用户'

        # 连接状态
        self.connected = False
        self.running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 3  # 秒

        # WebSocket 相关
        self.ws = None
        self._lock = threading.Lock()

        # 回调函数
        self.on_connected_callback = None
        self.on_disconnected_callback = None
        self.on_user_list_callback = None

    def set_nickname(self, nickname: str):
        """设置昵称"""
        self.nickname = nickname.strip() or '匿名用户'
        if self.connected:
            self._send_join_message()

    def set_callbacks(self, on_connected: Optional[Callable] = None,
                      on_disconnected: Optional[Callable] = None,
                      on_user_list: Optional[Callable] = None):
        """设置回调函数"""
        self.on_connected_callback = on_connected
        self.on_disconnected_callback = on_disconnected
        self.on_user_list_callback = on_user_list

    def start(self):
        """启动服务"""
        if self.running:
            return

        self.running = True
        self.reconnect_attempts = 0
        threading.Thread(target=self._run_websocket, daemon=True, name="WebSocketThread").start()

    def stop(self):
        """停止服务"""
        self.running = False
        with self._lock:
            if self.ws:
                try:
                    self.ws.close()
                except:
                    pass
                self.ws = None
        self.connected = False

    def send_message(self, message: str):
        """发送消息"""
        if not message.strip() or not self.connected:
            return
        data = {
            'type': 'message',
            'message': message.strip(),
            'timestamp': time.time()
        }
        self._send_json(data)

    def send_typing_status(self, is_typing: bool):
        """发送输入状态"""
        if self.connected:
            data = {
                'type': 'typing',
                'is_typing': is_typing
            }
            self._send_json(data)

    def _send_join_message(self):
        """发送加入消息"""
        data = {
            'type': 'join',
            'nickname': self.nickname
        }
        self._send_json(data)

    def _send_json(self, data: dict):
        """发送JSON数据"""
        with self._lock:
            if self.connected and self.ws:
                try:
                    self.ws.send(json.dumps(data))
                except Exception as e:
                    logger.error(f"发送消息失败: {e}")
                    self.connected = False

    def _run_websocket(self):
        """运行WebSocket连接"""
        while self.running and self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                logger.info(f"尝试连接到 {self.server_url}")

                self.ws = websocket.WebSocketApp(
                    self.server_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_close=self._on_close,
                    on_error=self._on_error
                )

                self.ws.run_forever(ping_interval=30, ping_timeout=10)

            except Exception as e:
                logger.error(f"WebSocket异常: {e}")

            # 重连逻辑
            if self.running:
                self.reconnect_attempts += 1
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    logger.info(f"{self.reconnect_delay}秒后尝试重连...")
                    time.sleep(self.reconnect_delay)
                else:
                    logger.error("达到最大重连次数，停止重连")

    def _on_open(self, ws):
        """连接打开回调"""
        logger.info("WebSocket连接已建立")
        self.connected = True
        self.reconnect_attempts = 0

        # 发送加入消息
        self._send_join_message()

        # 调用连接回调
        if self.on_connected_callback:
            self.on_connected_callback()

    def _on_message(self, ws, message):
        """收到消息回调"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')

            if msg_type == 'message':
                # 普通消息
                nickname = data.get('nickname', '未知用户')
                msg_content = data.get('message', '')
                timestamp = data.get('timestamp', time.time())

                if self.on_message_callback:
                    self.on_message_callback(nickname, msg_content, timestamp)

            elif msg_type == 'system':
                # 系统消息
                sys_msg = data.get('message', '')
                if self.on_message_callback:
                    self.on_message_callback('系统', sys_msg, time.time())

            elif msg_type == 'user_list':
                # 用户列表
                if self.on_user_list_callback:
                    users = data.get('users', [])
                    count = data.get('count', 0)
                    self.on_user_list_callback(users, count)

            elif msg_type == 'typing':
                # 输入状态
                nickname = data.get('nickname', '')
                is_typing = data.get('is_typing', False)
                # 可以添加输入状态回调处理

        except json.JSONDecodeError as e:
            logger.error(f"消息解析失败: {e}, 原始消息: {message}")

    def _on_close(self, ws, close_status_code, close_msg):
        """连接关闭回调"""
        logger.info(f"WebSocket连接已关闭: {close_status_code} - {close_msg}")
        self.connected = False

        if self.on_disconnected_callback:
            self.on_disconnected_callback(close_status_code, close_msg)

    def _on_error(self, ws, error):
        """错误回调"""
        logger.error(f"WebSocket错误: {error}")
        self.connected = False