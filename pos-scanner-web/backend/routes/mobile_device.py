# backend/routes/mobile_device.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from extensions import db
from models import User, MobileDevice
from datetime import datetime
import os
import functools

mobile_bp = Blueprint('mobile', __name__)

UPLOAD_FOLDER = 'uploads/mobile_devices'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_local_now():
    return datetime.now()


def admin_required(fn):
    """管理员权限装饰器"""
    @jwt_required()
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({'success': False, 'error': '需要管理员权限'}), 403
        return fn(*args, **kwargs)
    return wrapper


# ============ 设备管理 (管理员) ============

@mobile_bp.route('/devices', methods=['GET'])
@jwt_required()
def get_devices():
    """获取所有移动设备"""
    devices = MobileDevice.query.order_by(MobileDevice.created_at.desc()).all()
    return jsonify({
        'success': True,
        'devices': [d.to_dict() for d in devices]
    })


@mobile_bp.route('/devices', methods=['POST'])
@admin_required
def create_device():
    """创建移动设备（管理员）"""
    data = request.get_json()
    name = data.get('name')
    device_type = data.get('deviceType', '')
    system_version = data.get('systemVersion', '')

    if not name:
        return jsonify({'success': False, 'error': '设备名称不能为空'}), 400

    device = MobileDevice(
        name=name,
        device_type=device_type,
        system_version=system_version
    )
    db.session.add(device)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '设备创建成功',
        'device': device.to_dict()
    })


@mobile_bp.route('/devices/<int:device_id>', methods=['PUT'])
@admin_required
def update_device(device_id):
    """更新移动设备（管理员）"""
    device = MobileDevice.query.get(device_id)
    if not device:
        return jsonify({'success': False, 'error': '设备不存在'}), 404

    data = request.get_json()
    if data.get('name'):
        device.name = data['name']
    if 'deviceType' in data:
        device.device_type = data['deviceType']
    if 'systemVersion' in data:
        device.system_version = data['systemVersion']
    if 'imageA' in data:
        device.image_a = data['imageA']
    if 'imageB' in data:
        device.image_b = data['imageB']

    db.session.commit()

    return jsonify({
        'success': True,
        'message': '设备更新成功',
        'device': device.to_dict()
    })


@mobile_bp.route('/devices/<int:device_id>', methods=['DELETE'])
@admin_required
def delete_device(device_id):
    """删除移动设备（管理员）"""
    device = MobileDevice.query.get(device_id)
    if not device:
        return jsonify({'success': False, 'error': '设备不存在'}), 404

    # 删除关联的图片
    if device.image_a:
        try:
            os.remove(os.path.join(current_app.root_path, device.image_a))
        except:
            pass
    if device.image_b:
        try:
            os.remove(os.path.join(current_app.root_path, device.image_b))
        except:
            pass

    db.session.delete(device)
    db.session.commit()

    return jsonify({'success': True, 'message': '设备已删除'})


@mobile_bp.route('/devices/<int:device_id>/upload', methods=['POST'])
@admin_required
def upload_image(device_id):
    """上传设备图片（管理员）"""
    device = MobileDevice.query.get(device_id)
    if not device:
        return jsonify({'success': False, 'error': '设备不存在'}), 404

    if 'image' not in request.files:
        return jsonify({'success': False, 'error': '没有上传文件'}), 400

    file = request.files['image']
    image_type = request.form.get('type', 'a')  # a 或 b

    if file.filename == '':
        return jsonify({'success': False, 'error': '没有选择文件'}), 400

    if file and allowed_file(file.filename):
        # 确保上传目录存在
        upload_dir = os.path.join(current_app.root_path, UPLOAD_FOLDER)
        os.makedirs(upload_dir, exist_ok=True)

        # 生成文件名
        filename = secure_filename(f"{device_id}_{image_type}_{file.filename}")
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        # 保存相对路径
        relative_path = os.path.join(UPLOAD_FOLDER, filename)
        if image_type == 'a':
            device.image_a = relative_path
        else:
            device.image_b = relative_path

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '图片上传成功',
            'path': relative_path
        })

    return jsonify({'success': False, 'error': '不支持的文件格式'}), 400


# ============ 占用管理 (所有用户) ============

@mobile_bp.route('/devices/<int:device_id>/occupy', methods=['PUT'])
@jwt_required()
def set_occupancy(device_id):
    """设置设备占用（所有用户）"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 401

    device = MobileDevice.query.get(device_id)
    if not device:
        return jsonify({'success': False, 'error': '设备不存在'}), 404

    data = request.get_json()
    purpose = data.get('purpose', '')
    end_time_str = data.get('endTime')

    if not end_time_str:
        return jsonify({'success': False, 'error': '结束时间不能为空'}), 400

    # 解析时间
    end_time_str = end_time_str.replace('Z', '+00:00')
    if '.' in end_time_str:
        parts = end_time_str.split('.')
        end_time_str = parts[0] + parts[1][-6:]
    try:
        end_time = datetime.fromisoformat(end_time_str)
        if end_time.tzinfo is not None:
            end_time = end_time.replace(tzinfo=None)
    except Exception as e:
        return jsonify({'success': False, 'error': f'时间格式错误: {str(e)}'}), 400

    # 设置占用
    device.occupier_id = user_id
    device.purpose = purpose
    device.start_time = get_local_now()
    device.end_time = end_time

    db.session.commit()

    return jsonify({
        'success': True,
        'message': '占用成功',
        'device': device.to_dict()
    })


@mobile_bp.route('/devices/<int:device_id>/release', methods=['PUT'])
@jwt_required()
def release_occupancy(device_id):
    """释放设备占用"""
    user_id = int(get_jwt_identity())
    device = MobileDevice.query.get(device_id)

    if not device:
        return jsonify({'success': False, 'error': '设备不存在'}), 404

    # 只有占用人本人或管理员可以释放
    user = User.query.get(user_id)
    if device.occupier_id != user_id and (not user or user.role != 'admin'):
        return jsonify({'success': False, 'error': '无权释放此设备'}), 403

    device.occupier_id = None
    device.purpose = None
    device.start_time = None
    device.end_time = None

    db.session.commit()

    return jsonify({
        'success': True,
        'message': '设备已释放',
        'device': device.to_dict()
    })


def cleanup_expired_occupancies():
    """清理过期的占用"""
    now = get_local_now()
    expired = MobileDevice.query.filter(
        MobileDevice.end_time is not None,
        MobileDevice.end_time < now
    ).all()
    for device in expired:
        device.occupier_id = None
        device.purpose = None
        device.start_time = None
        device.end_time = None
    if expired:
        db.session.commit()
    return len(expired)
