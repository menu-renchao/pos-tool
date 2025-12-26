import threading
import time
import io
import csv
from flask import Flask, jsonify, request, send_file
from pos_tool_new.scan_pos import scan_pos_service

app = Flask(__name__)

scan_result = {
    'progress': 0,
    'data': [],
    'finished': False
}
scan_lock = threading.Lock()
scan_thread = None


def scan_task():
    global scan_result
    # 清空结果
    with scan_lock:
        scan_result['progress'] = 0
        scan_result['data'] = []
        scan_result['finished'] = False
    # 假设scan_pos_service有scan_all_pos方法，返回扫描结果列表
    # 你需要根据实际情况调整参数和调用方式
    result = []
    total = 100  # 假设100步进度
    for i in range(total):
        time.sleep(0.05)  # 模拟扫描耗时
        # 这里应调用真实的扫描逻辑
        # result.append(...)
        with scan_lock:
            scan_result['progress'] = int((i + 1) / total * 100)
    # 实际扫描
    result = scan_pos_service.scan_all_pos()
    with scan_lock:
        scan_result['data'] = result
        scan_result['progress'] = 100
        scan_result['finished'] = True


@app.route('/api/scan/start', methods=['POST'])
def start_scan():
    global scan_thread
    if scan_thread and scan_thread.is_alive():
        return jsonify({'msg': '扫描已在进行中'}), 400
    scan_thread = threading.Thread(target=scan_task)
    scan_thread.start()
    return jsonify({'msg': '扫描已启动'})


@app.route('/api/scan/result', methods=['GET'])
def get_scan_result():
    with scan_lock:
        return jsonify({
            'progress': scan_result['progress'],
            'data': scan_result['data'],
            'finished': scan_result['finished']
        })


@app.route('/api/scan/export', methods=['GET'])
def export_scan_result():
    with scan_lock:
        data = scan_result['data']
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['IP', '设备类型', '状态'])
    for row in data:
        writer.writerow([
            row.get('ip', ''),
            row.get('deviceType', ''),
            row.get('status', '')
        ])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='scan_result.csv'
    )

if __name__ == '__main__':
    app.run(port=5000, debug=True)

