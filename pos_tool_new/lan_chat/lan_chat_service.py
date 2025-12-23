# 消息广播服务，负责消息收发
import socket
import threading
import json
from pos_tool_new.backend import Backend

BROADCAST_PORT = 56789
BROADCAST_ADDR = '<broadcast>'
BUFFER_SIZE = 4096

class LanChatService(Backend):
    def __init__(self, on_message_callback):
        super().__init__()
        self.nickname = '匿名'
        self.on_message_callback = on_message_callback
        self.running = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', BROADCAST_PORT))

    def set_nickname(self, nickname):
        self.nickname = nickname

    def send_message(self, message):
        if isinstance(message, dict):
            data = json.dumps({'nickname': self.nickname, **message})
        else:
            data = json.dumps({'nickname': self.nickname, 'type': 'text', 'message': message})
        self.sock.sendto(data.encode('utf-8'), (BROADCAST_ADDR, BROADCAST_PORT))

    def start_listen(self):
        self.running = True
        threading.Thread(target=self._listen, daemon=True).start()

    def stop(self):
        self.running = False
        self.sock.close()

    def _listen(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                msg = json.loads(data.decode('utf-8'))
                if self.on_message_callback:
                    # 只传递字符串内容，界面只显示消息文本
                    if 'type' in msg and msg['type'] == 'text':
                        self.on_message_callback(msg['nickname'], msg.get('message', ''))
                    else:
                        self.on_message_callback(msg['nickname'], msg.get('message', ''))
            except Exception:
                break
