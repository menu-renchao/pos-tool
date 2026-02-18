"""
模拟 POS 设备服务器
用于测试扫描功能
运行: python mock_pos_device.py
"""
from flask import Flask, jsonify
import socket

app = Flask(__name__)

# 模拟设备信息
MOCK_DEVICES = {
    "company": {
        "merchantId": "MOCK001",
        "name": "测试门店",
        "appInfo": {
            "version": "1.5.1"
        }
    }
}


@app.route('/kpos/webapp/store/fetchCompanyProfile', methods=['GET'])
def fetch_company_profile():
    """返回设备信息"""
    return jsonify(MOCK_DEVICES)


@app.route('/kpos/webapp/os/getOSType', methods=['GET'])
def get_os_type():
    """返回操作系统类型"""
    return jsonify({"os": "Android"})


@app.route('/', methods=['GET'])
def index():
    """根路径"""
    return jsonify({"message": "Mock POS Device Server", "port": 22080})


def get_local_ip():
    """获取本地IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"\n{'='*50}")
    print(f"  模拟 POS 设备服务器已启动")
    print(f"{'='*50}")
    print(f"  本地 IP: {local_ip}:22080")
    print(f"  API 端点:")
    print(f"    - http://{local_ip}:22080/kpos/webapp/store/fetchCompanyProfile")
    print(f"    - http://{local_ip}:22080/kpos/webapp/os/getOSType")
    print(f"{'='*50}\n")

    app.run(host='0.0.0.0', port=22080, debug=False)
