from flask import Flask, request, jsonify
from flask_cors import CORS
from scan_service import ScanPosService
import threading
from concurrent.futures import ThreadPoolExecutor
import json
from config import Config
import concurrent.futures
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# 新增导入
from extensions import db, jwt
from models import User, ScanResult, ScanSession
from routes.auth import auth_bp
from routes.admin import admin_bp
from flask_jwt_extended import JWTManager

app = Flask(__name__)
app.config.from_object(Config)

# 初始化扩展
db.init_app(app)
jwt.init_app(app)

CORS(app, origins=app.config['CORS_ORIGINS'])

# JWT 错误处理器
@jwt.invalid_token_loader
def invalid_token_callback(error_string):
    print(f"Invalid token: {error_string}")
    return jsonify({'success': False, 'error': 'Invalid token', 'msg': error_string}), 422

@jwt.unauthorized_loader
def missing_token_callback(error_string):
    print(f"Missing token: {error_string}")
    return jsonify({'success': False, 'error': 'Token required', 'msg': error_string}), 401

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    print(f"Expired token: {jwt_payload}")
    return jsonify({'success': False, 'error': 'Token expired'}), 401

@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    return jsonify({'success': False, 'error': 'Token revoked'}), 401

# 注册认证蓝图
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(admin_bp, url_prefix='/api/admin')

# 存储扫描状态和结果
scan_status = {
    'is_scanning': False,
    'progress': 0,
    'current_ip': '',
    'results': [],
    'error': None
}

executor = ThreadPoolExecutor(max_workers=1)


# 数据库初始化标志
_db_initialized = False


def cleanup_old_results():
    """清理超过24小时的扫描结果"""
    try:
        threshold = datetime.utcnow() - timedelta(hours=24)
        deleted = ScanResult.query.filter(ScanResult.scanned_at < threshold).delete()
        if deleted > 0:
            logger.info(f"已清理 {deleted} 条过期扫描结果")
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"清理过期数据失败: {e}")


def init_db():
    """初始化数据库和默认管理员"""
    global _db_initialized
    if _db_initialized:
        return

    db.create_all()
    # 创建默认管理员
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', role='admin', status='approved')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

    # 初始化扫描会话
    ScanSession.get_session()

    # 清理过期数据
    cleanup_old_results()

    _db_initialized = True


@app.before_request
def before_request():
    """请求前初始化数据库"""
    init_db()


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

        # 清空旧结果
        ScanResult.query.delete()
        db.session.commit()

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

            # 保存每个结果到数据库
            scan_result = ScanResult(
                ip=result['ip'],
                merchant_id=result.get('merchantId', ''),
                name=result.get('name', ''),
                version=result.get('version', ''),
                type=result.get('type', ''),
                full_data=json.dumps(result.get('fullData', {}))
            )
            db.session.add(scan_result)

        # 更新扫描时间并提交
        session = ScanSession.get_session()
        session.last_scan_at = datetime.utcnow()
        db.session.commit()

        scan_status['is_scanning'] = False
        scan_status['progress'] = 100

    except Exception as e:
        db.session.rollback()
        scan_status['is_scanning'] = False
        scan_status['error'] = str(e)
        logger.error(f"扫描失败: {e}")


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
    results = ScanResult.query.all()
    session = ScanSession.get_session()

    return jsonify({
        'success': True,
        'devices': [r.to_dict() for r in results],
        'lastScanAt': session.last_scan_at.isoformat() if session.last_scan_at else None
    })


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
    with app.app_context():
        init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
