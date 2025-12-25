# lan_chat_service.py
import websocket
import threading
import json
import time
from typing import Callable, Optional
from pos_tool_new.backend import Backend


class LanChatService(Backend):
    def __init__(self, on_message_callback: Callable, server_url: str = 'ws://localhost:56789'):
        super().__init__()
        self.server_url = server_url
        self.on_message_callback = on_message_callback
        self.nickname = '匿名用户'
        self.connected = self.running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 3
        self.ws = None
        self._lock = threading.Lock()
        self.on_connected_callback = self.on_disconnected_callback = self.on_user_list_callback = None

    def set_nickname(self, nickname: str):
        self.nickname = nickname.strip() or '匿名用户'
        if self.connected:
            self._send_json({'type': 'join', 'nickname': self.nickname})

    def set_callbacks(self, on_connected: Optional[Callable] = None,
                      on_disconnected: Optional[Callable] = None,
                      on_user_list: Optional[Callable] = None):
        self.on_connected_callback = on_connected
        self.on_disconnected_callback = on_disconnected
        self.on_user_list_callback = on_user_list

    def start(self):
        if not self.running:
            self.running = True
            self.reconnect_attempts = 0
            threading.Thread(target=self._run_websocket, daemon=True).start()

    def stop(self):
        self.running = False
        with self._lock:
            if self.ws:
                try:
                    self.ws.close()
                except:
                    pass
                self.ws = None
        self.connected = False

    def send_message(self, message: str, marquee: bool = False):
        if message.strip() and self.connected:
            self._send_json({'type': 'message', 'message': message.strip(), 'timestamp': time.time(), 'marquee': marquee})

    def send_typing_status(self, is_typing: bool):
        if self.connected:
            self._send_json({'type': 'typing', 'is_typing': is_typing})

    def _send_json(self, data: dict):
        with self._lock:
            if self.connected and self.ws:
                try:
                    self.ws.send(json.dumps(data))
                except Exception as e:
                    self.log(f"发送消息失败: {e}", "error")
                    self.connected = False

    def _run_websocket(self):
        while self.running and self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                self.log(f"尝试连接到 {self.server_url}")
                self.ws = websocket.WebSocketApp(
                    self.server_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_close=self._on_close,
                    on_error=self._on_error
                )
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                self.log(f"WebSocket异常: {e}", "error")
            if self.running:
                self.reconnect_attempts += 1
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    self.log(f"{self.reconnect_delay}秒后尝试重连...")
                    time.sleep(self.reconnect_delay)
                else:
                    self.log("达到最大重连次数，停止重连", "error")

    def _on_open(self, ws):
        self.log("WebSocket连接已建立")
        self.connected = True
        self.reconnect_attempts = 0
        self._send_json({'type': 'join', 'nickname': self.nickname})
        if self.on_connected_callback:
            self.on_connected_callback()

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            if msg_type == 'message' and self.on_message_callback:
                self.on_message_callback(
                    data.get('nickname', '未知用户'),
                    data.get('message', ''),
                    data.get('timestamp', time.time()),
                    data.get('marquee', False)
                )
            elif msg_type == 'system' and self.on_message_callback:
                self.on_message_callback('系统', data.get('message', ''), time.time())
            elif msg_type == 'user_list' and self.on_user_list_callback:
                self.on_user_list_callback(data.get('users', []), data.get('count', 0))
            # 新增：处理 latest_user_message
            elif msg_type == 'latest_user_message' and self.on_message_callback:
                # 只传递内容，不带昵称
                self.on_message_callback('', data.get('message', ''), data.get('timestamp', time.time()))
        except json.JSONDecodeError as e:
            self.log(f"消息解析失败: {e}, 原始消息: {message}", "error")

    def _on_close(self, ws, close_status_code, close_msg):
        self.log(f"WebSocket连接已关闭: {close_status_code} - {close_msg}")
        self.connected = False
        if self.on_disconnected_callback:
            self.on_disconnected_callback(close_status_code, close_msg)

    def _on_error(self, ws, error):
        self.log(f"WebSocket错误: {error}", "error")
        self.connected = False

    def reconnect(self):
        """
        手动重连：重置重连次数并立即尝试重连。
        可用于UI按钮调用，防止自动重连次数耗尽后无法再连。
        """
        self.stop()
        self.reconnect_attempts = 0
        self.start()
