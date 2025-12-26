from flask import Flask, request, jsonify
from flask_cors import CORS
from scan_service import ScanPosService
import threading
from concurrent.futures import ThreadPoolExecutor
import json
from config import Config
import concurrent.futures

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, origins=app.config['CORS_ORIGINS'])

# 存储扫描状态和结果
scan_status = {
    'is_scanning': False,
    'progress': 0,
    'current_ip': '',
    'results': [],
    'error': None
}

executor = ThreadPoolExecutor(max_workers=1)


@app.route('/api/scan/ips', methods=['GET'])
def get_local_ips():
    """获取本地IP地址列表"""
    try:
        service = ScanPosService()
        ips = service.get_local_ips()
        return jsonify({'success': True, 'ips': ips})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/scan/start', methods=['POST'])
def start_scan():
    """开始扫描"""
    global scan_status

    if scan_status['is_scanning']:
        return jsonify({'success': False, 'error': '扫描正在进行中'})

    data = request.get_json()
    local_ip = data.get('local_ip')

    if not local_ip:
        return jsonify({'success': False, 'error': '未选择IP地址'})

    # 重置扫描状态
    scan_status = {
        'is_scanning': True,
        'progress': 0,
        'current_ip': '',
        'results': [],
        'error': None
    }

    # 在后台线程中执行扫描
    executor.submit(perform_scan, local_ip)

    return jsonify({'success': True, 'message': '扫描已开始'})


def perform_scan(local_ip):
    """执行扫描任务"""
    global scan_status
    try:
        service = ScanPosService(local_ip=local_ip)

        # 获取网络范围
        network = service._get_local_network()
        hosts = list(network.hosts())
        total_hosts = len(hosts)

        # 扫描开放端口
        open_ips = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=200) as port_executor:
            futures = {port_executor.submit(service._scan_port, ip, 22080): ip for ip in hosts}
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                scan_status['progress'] = (i + 1) * 50 // total_hosts  # 端口扫描占50%
                scan_status['current_ip'] = str(futures[future])

                if future.result():
                    open_ips.append(str(future.result()))

        # 获取设备信息
        total_open = len(open_ips)
        for i, ip in enumerate(open_ips):
            scan_status['progress'] = 50 + (i + 1) * 50 // total_open  # 信息获取占50%
            scan_status['current_ip'] = ip

            result = service._fetch_and_process(ip, 22080)
            scan_status['results'].append(result)

        scan_status['is_scanning'] = False
        scan_status['progress'] = 100

    except Exception as e:
        scan_status['is_scanning'] = False
        scan_status['error'] = str(e)


@app.route('/api/scan/status', methods=['GET'])
def get_scan_status():
    """获取扫描状态"""
    return jsonify(scan_status)


@app.route('/api/scan/stop', methods=['POST'])
def stop_scan():
    """停止扫描"""
    global scan_status
    scan_status['is_scanning'] = False
    return jsonify({'success': True, 'message': '扫描已停止'})


@app.route('/api/devices', methods=['GET'])
def get_devices():
    """获取所有设备列表"""
    return jsonify({'success': True, 'devices': scan_status['results']})


@app.route('/api/device/<ip>/details', methods=['GET'])
def get_device_details(ip):
    """获取设备详情"""
    try:
        service = ScanPosService()
        full_data = service.fetch_company_profile(ip)

        # 过滤不需要的字段
        def filter_data(data):
            exclude_keys = {"appInstance", "images", "result", "printLogo"}
            if isinstance(data, dict):
                return {k: filter_data(v) for k, v in data.items()
                        if v is not None and k not in exclude_keys}
            elif isinstance(data, list):
                return [filter_data(item) for item in data if item is not None]
            else:
                return data

        filtered_data = filter_data(full_data)
        return jsonify({'success': True, 'data': filtered_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)