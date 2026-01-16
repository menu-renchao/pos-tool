import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
import logging
from flask import Flask, jsonify, send_file, request, abort
import os
import re
import json
import websockets
from datetime import datetime
from playwright.sync_api import sync_playwright

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('integrated_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class IntegratedServer:
    def __init__(self):
        self.chat_server = ChatServer()
        self.playwright_app = PlaywrightService()
        self.flask_app = Flask(__name__)
        self.setup_flask_routes()

    def setup_flask_routes(self):
        """设置所有Flask路由"""

        # 版本管理服务路由
        @self.flask_app.route('/api/version', methods=['GET'])
        def get_version():
            _, version = self.get_latest_exe_info()
            info = self.get_latest_version_info()
            if version:
                return jsonify({'version': version, 'info': info})
            else:
                return jsonify({'error': 'No exe found'}), 404

        @self.flask_app.route('/api/download', methods=['GET'])
        def download_exe():
            exe_path, version = self.get_latest_exe_info()
            if exe_path and os.path.exists(exe_path):
                return send_file(exe_path, as_attachment=True,
                                 download_name=f'PosTestUtil_v{version}.exe')
            else:
                abort(404, 'No exe found')

        # Playwright服务路由
        @self.flask_app.route('/api/usable_phone_numbers', methods=['GET'])
        def api_usable_phone_numbers():
            logger.info("收到请求: /api/usable_phone_numbers")
            try:
                phone_list = self.playwright_app.get_usable_phone_numbers()
                logger.info(f"返回手机号列表: {phone_list}")
                return jsonify({"phone_numbers": phone_list})
            except Exception as e:
                logger.error(f"获取手机号异常: {e}")
                return jsonify({"phone_numbers": [], "error": str(e)}), 500

        @self.flask_app.route('/api/latest_code', methods=['POST'])
        def api_latest_code():
            data = request.get_json(force=True)
            phone_number = data.get("phone_number", "")
            keyword = data.get("keyword", "")
            count = int(data.get("count", 1))
            logger.info(f"收到请求: /api/latest_code, phone_number={phone_number}, keyword={keyword}, count={count}")
            try:
                result = self.playwright_app.get_latest_code(phone_number, keyword, count)
                logger.info(f"返回短信内容: {result}")
                return jsonify({"result": result})
            except Exception as e:
                logger.error(f"获取短信异常: {e}")
                return jsonify({"result": "", "error": str(e)}), 500

        # 健康检查路由
        @self.flask_app.route('/health', methods=['GET'])
        def health_check():
            return jsonify({
                'status': 'healthy',
                'services': {
                    'websocket_chat': 'running',
                    'version_management': 'running',
                    'sms_service': 'running'
                }
            })

    # 版本管理相关方法
    def get_latest_exe_info(self):
        """查找build目录下最新版本的exe文件和版本号"""
        BUILD_DIR = "E:\service"
        EXE_PREFIX = 'PosTestUtil_v'
        EXE_SUFFIX = '.exe'

        if not os.path.exists(BUILD_DIR):
            return None, None
        version_pattern = re.compile(rf'{EXE_PREFIX}(\d+\.\d+\.\d+\.\d+){EXE_SUFFIX}')
        latest_version = None
        latest_exe = None
        for root, dirs, files in os.walk(BUILD_DIR):
            for file in files:
                match = version_pattern.match(file)
                if match:
                    version = match.group(1)
                    if (latest_version is None) or (
                            tuple(map(int, version.split('.'))) > tuple(map(int, latest_version.split('.')))):
                        latest_version = version
                        latest_exe = os.path.join(root, file)
        return latest_exe, latest_version

    def get_latest_version_info(self):
        """解析 version_info.html，返回最新版本的升级说明内容"""
        html_path = "E:\\service\\version_info.html"
        if not os.path.exists(html_path):
            return ''
        with open(html_path, encoding='utf-8') as f:
            html = f.read()
        h3_match = re.search(r'<h3>\s*v([\d.]+)[(（]最新版本[)）]\s*</h3>', html, re.I)
        if not h3_match:
            return ''
        h3_end = h3_match.end()
        ul_match = re.search(r'<ul>(.*?)</ul>', html[h3_end:], re.I | re.S)
        if not ul_match:
            return ''
        ul_content = ul_match.group(1)
        items = re.findall(r'<li>(.*?)</li>', ul_content, re.I | re.S)
        info = '\n'.join(item.strip() for item in items)
        return info

    async def start_websocket_server(self):
        """启动WebSocket聊天服务器"""
        try:
            async with websockets.serve(self.chat_server.handle_connection,
                                        self.chat_server.host, self.chat_server.port):
                logger.info(f"WebSocket聊天服务器启动在 {self.chat_server.host}:{self.chat_server.port}")
                await asyncio.Future()  # 永久运行
        except OSError as e:
            if getattr(e, 'winerror', None) == 64:
                logger.warning("WebSocket服务器遇到 WinError 64（指定的网络名不再可用），通常为客户端异常断开，可忽略。")
            else:
                logger.error(f"WebSocket服务器发生 OSError: {e}")
        except Exception as e:
            logger.error(f"WebSocket服务器发生未知异常: {e}")

    def start_flask_server(self):
        """启动Flask HTTP服务器"""
        logger.info(f"HTTP服务器启动在 0.0.0.0:5001")
        self.flask_app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)

    async def run_all_services(self):
        """启动所有服务"""
        # 在线程中运行Flask服务器
        flask_thread = threading.Thread(target=self.start_flask_server, daemon=True)
        flask_thread.start()

        # 运行WebSocket服务器（主线程）
        await self.start_websocket_server()


class ChatServer:
    """WebSocket聊天服务器"""

    def __init__(self, host='0.0.0.0', port=56789):
        self.host = host
        self.port = port
        self.clients = {}
        self.latest_user_message = None

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
                            if msg_content.strip() and marquee_flag:
                                self.latest_user_message = msg_content
                            message_data = {
                                'type': 'message',
                                'nickname': user_info['nickname'],
                                'message': msg_content,
                                'timestamp': datetime.now().isoformat(),
                                'marquee': marquee_flag
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


class PlaywrightService:
    """Playwright短信服务"""

    def __init__(self):
        # 设置浏览器路径
        user_home = os.path.expanduser("~")
        browser_dir = os.path.join(user_home, "AppData", "Local", "ms-playwright")
        os.makedirs(browser_dir, exist_ok=True)
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browser_dir

    def get_headers(self):
        return {
            "User-Agent": "Mozilla/5.180441367190 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Referer": "https://www.google.com/"
        }

    def get_latest_code(self, phone_number, keyword, count=1):
        """获取最新验证码"""
        if phone_number == '' or not phone_number or phone_number == '请选择手机号':
            return "请输入手机号"
        url = f"https://receive-sms-free.cc/Free-USA-Phone-Number/{phone_number}/"
        logger.info(f"访问的 URL: {url}")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_extra_http_headers(self.get_headers())
                page.goto(url)
                page.wait_for_timeout(1000)

                messages = page.query_selector_all("div.casetext div.row")
                matched_messages = []

                for message in messages:
                    text = message.inner_text().split("\n")
                    logger.debug(f"解析消息: {text}")
                    if text == ['From', 'Time', 'Message']:
                        continue
                    if len(text) == 3 and (not keyword or keyword in text[2]):
                        matched_messages.append(
                            f"From: {text[0]}, "
                            f"Time: {text[1]}, "
                            f"Content: {text[2]}"
                        )
                        if len(matched_messages) >= count:
                            break

                browser.close()
                return "\n\n".join(matched_messages) if matched_messages else ""
        except Exception as e:
            logger.error(f"获取短信发生错误: {e}")
            return ""

    def get_usable_phone_numbers(self):
        """获取可用手机号"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_extra_http_headers(self.get_headers())
                page.goto("https://receive-sms-free.cc/")
                page.wait_for_timeout(1000)

                messages = page.query_selector_all("h2.h2 span")
                phone_list = [message.text_content() for message in messages if message.text_content().startswith('+1')]
                logger.info(f"可用手机号列表: {phone_list}")
                browser.close()
                return phone_list
        except Exception as e:
            logger.error(f"获取手机号发生错误: {e}")
            return []


async def main():
    """主函数"""
    server = IntegratedServer()
    logger.info("开始启动集成服务器...")
    await server.run_all_services()


if __name__ == "__main__":
    # 创建启动脚本
    startup_script = """
# 启动集成服务
import asyncio
from main_server import main

if __name__ == "__main__":
    asyncio.run(main())
"""

    # 将启动脚本写入文件
    with open("start_server.py", "w", encoding="utf-8") as f:
        f.write(startup_script)

    logger.info("启动脚本已生成: start_server.py")
    logger.info("正在启动集成服务器...")

    # 运行主服务
    asyncio.run(main())