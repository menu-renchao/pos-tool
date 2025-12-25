import asyncio
import websockets
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChatServer:
    def __init__(self, host='0.0.0.0', port=56789):
        self.host = host
        self.port = port
        self.clients = {}
        self.latest_user_message = None  # 新增：保存最新用户消息内容

    async def handle_connection(self, websocket, path):
        client_id = id(websocket)
        logger.info(f"客户端 {client_id} 连接成功")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type', 'message')
                    if message_type == 'join':
                        nickname = data.get('nickname', f'用户{client_id}')
                        self.clients[websocket] = {
                            'nickname': nickname,
                            'join_time': datetime.now().isoformat()
                        }
                        await self.broadcast_user_list()
                        await self.broadcast_system_message(f"{nickname} 加入了聊天")
                        logger.info(f"用户 {nickname} 加入聊天室")
                        # 新增：有新用户加入时，推送最新用户消息
                        if self.latest_user_message:
                            await websocket.send(json.dumps({
                                'type': 'latest_user_message',
                                'message': self.latest_user_message,
                                'timestamp': datetime.now().isoformat()
                            }))
                    elif message_type == 'message':
                        if websocket in self.clients:
                            user_info = self.clients[websocket]
                            msg_content = data.get('message', '')
                            marquee_flag = data.get('marquee', False)
                            # 新增：只保存勾选跑马灯的消息
                            if msg_content.strip() and marquee_flag:
                                self.latest_user_message = msg_content
                            message_data = {
                                'type': 'message',
                                'nickname': user_info['nickname'],
                                'message': msg_content,
                                'timestamp': datetime.now().isoformat(),
                                'marquee': marquee_flag  # 关键：加上这一行
                            }
                            await self.broadcast_message(json.dumps(message_data))
                    elif message_type == 'typing':
                        if websocket in self.clients:
                            typing_data = {
                                'type': 'typing',
                                'nickname': self.clients[websocket]['nickname'],
                                'is_typing': data.get('is_typing', False)
                            }
                            await self.broadcast_to_others(websocket, json.dumps(typing_data))
                except json.JSONDecodeError:
                    logger.warning(f"收到无效的JSON消息: {message}")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"客户端 {client_id} 连接断开")
        finally:
            if websocket in self.clients:
                nickname = self.clients[websocket]['nickname']
                del self.clients[websocket]
                await self.broadcast_user_list()
                await self.broadcast_system_message(f"{nickname} 离开了聊天")
                logger.info(f"用户 {nickname} 离开聊天室")

    async def broadcast_message(self, message):
        if self.clients:
            tasks = []
            for client in list(self.clients.keys()):
                try:
                    tasks.append(client.send(message))
                except:
                    if client in self.clients:
                        del self.clients[client]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_to_others(self, sender, message):
        tasks = []
        for client in list(self.clients.keys()):
            if client != sender:
                try:
                    tasks.append(client.send(message))
                except:
                    if client in self.clients:
                        del self.clients[client]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_user_list(self):
        user_list = {
            'type': 'user_list',
            'users': [info['nickname'] for info in self.clients.values()],
            'count': len(self.clients)
        }
        await self.broadcast_message(json.dumps(user_list))

    async def broadcast_system_message(self, message):
        system_msg = {
            'type': 'system',
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        await self.broadcast_message(json.dumps(system_msg))

server = ChatServer()

async def handler(websocket, path):
    await server.handle_connection(websocket, path)

if __name__ == "__main__":
    async def main():
        async with websockets.serve(handler, server.host, server.port):
            logger.info(f"聊天服务器启动在 {server.host}:{server.port}")
            await asyncio.Future()  # 永久运行
    asyncio.run(main())