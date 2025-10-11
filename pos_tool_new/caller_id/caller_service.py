# caller_service.py
import random
import socket
from datetime import datetime

from PyQt6.QtCore import QDate

from pos_tool_new.backend import Backend


class CallerService(Backend):
    """处理 Caller ID 相关逻辑的服务类"""

    @staticmethod
    def format_phone_number(number):
        """格式化电话号码为 XXX-XXX-XXXX 格式"""
        if len(number) == 10:
            return f"{number[:3]}-{number[3:6]}-{number[6:]}"
        return number

    @staticmethod
    def generate_packet(name, number):
        """生成 UDP 数据包"""
        current_date = QDate.currentDate().toString("yyyy-MM-dd")
        current_time = datetime.now().strftime("%H:%M")
        return f"DATE={current_date}\nTIME={current_time}\nNAME={name}\nNMBR={number}\nMOCK=true"

    @staticmethod
    def send_udp_packet(packet, ip, port=3520):
        """发送 UDP 数据包"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_client:
                bytes_data = packet.encode('ascii')
                udp_client.sendto(bytes_data, (ip, port))
                return True
        except Exception as e:
            raise Exception(f"UDP 发送失败: {str(e)}")

    @staticmethod
    def get_random_time_formatted():
        """生成随机时间"""
        rnd = random.Random()
        month = rnd.randint(1, 12)

        # 根据月份确定天数
        if month == 2:
            day = rnd.randint(1, 28)
        elif month in [4, 6, 9, 11]:
            day = rnd.randint(1, 30)
        else:
            day = rnd.randint(1, 31)

        hour = rnd.randint(1, 12)
        minute = rnd.randint(0, 59)
        period = "PM" if rnd.randint(0, 1) == 1 else "AM"

        return f"{month:02d}/{day:02d} {hour:02d}:{minute:02d} {period}"

    @staticmethod
    def get_current_time_formatted():
        """获取当前时间格式化为 MM/dd hh:mm tt"""
        return datetime.now().strftime("%m/%d %I:%M %p")

    @staticmethod
    def generate_random_name():
        """生成随机姓名"""
        first_names = ["John", "Emma", "Michael", "Sophia", "William",
                       "Olivia", "James", "Ava", "Benjamin", "Isabella"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones",
                      "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]

        return f"{random.choice(first_names)} {random.choice(last_names)}"

    @staticmethod
    def generate_random_phone_number():
        """生成随机电话号码"""
        return ''.join(str(random.randint(0, 9)) for _ in range(10))
