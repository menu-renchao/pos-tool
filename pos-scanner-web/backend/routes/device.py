# backend/routes/device.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import User, DeviceOccupancy
from datetime import datetime

device_bp = Blueprint('device', __name__)


def get_local_now():
    """获取本地时间"""
    return datetime.now()


@device_bp.route('/occupancy', methods=['GET'])
@jwt_required()
def get_occupancies():
    """获取所有设备占用信息"""
    occupancies = DeviceOccupancy.query.all()
    return jsonify({
        'success': True,
        'occupancies': [o.to_dict() for o in occupancies]
    })


@device_bp.route('/occupancy', methods=['PUT'])
@jwt_required()
def set_occupancy():
    """设置设备占用（所有用户可用）"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 401

    data = request.get_json()
    merchant_id = data.get('merchant_id')
    purpose = data.get('purpose', '')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')

    if not merchant_id:
        return jsonify({'success': False, 'error': '商家ID不能为空'}), 400

    if not end_time_str:
        return jsonify({'success': False, 'error': '结束时间不能为空'}), 400

    try:
        # 使用本地时间，避免时区问题
        if start_time_str:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            if start_time.tzinfo is not None:
                start_time = start_time.replace(tzinfo=None)
        else:
            start_time = get_local_now()

        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        if end_time.tzinfo is not None:
            end_time = end_time.replace(tzinfo=None)
    except ValueError:
        return jsonify({'success': False, 'error': '时间格式错误'}), 400

    if end_time <= start_time:
        return jsonify({'success': False, 'error': '结束时间必须大于开始时间'}), 400

    # 查找或创建
    occupancy = DeviceOccupancy.query.filter_by(merchant_id=merchant_id).first()
    if occupancy:
        # 更新占用信息
        occupancy.user_id = user_id
        occupancy.purpose = purpose
        occupancy.start_time = start_time
        occupancy.end_time = end_time
    else:
        occupancy = DeviceOccupancy(
            merchant_id=merchant_id,
            user_id=user_id,
            purpose=purpose,
            start_time=start_time,
            end_time=end_time
        )
        db.session.add(occupancy)

    db.session.commit()

    return jsonify({
        'success': True,
        'message': '占用信息已更新',
        'occupancy': occupancy.to_dict()
    })


@device_bp.route('/occupancy/<merchant_id>', methods=['DELETE'])
@jwt_required()
def release_occupancy(merchant_id):
    """释放设备占用"""
    user_id = int(get_jwt_identity())
    occupancy = DeviceOccupancy.query.filter_by(merchant_id=merchant_id).first()

    if not occupancy:
        return jsonify({'success': False, 'error': '占用信息不存在'}), 404

    # 只有占用人本人或管理员可以释放
    user = User.query.get(user_id)
    if occupancy.user_id != user_id and (not user or user.role != 'admin'):
        return jsonify({'success': False, 'error': '无权释放此设备'}), 403

    db.session.delete(occupancy)
    db.session.commit()

    return jsonify({'success': True, 'message': '设备已释放'})


def cleanup_expired_occupancies():
    """清理已过期的占用记录"""
    now = get_local_now()
    expired = DeviceOccupancy.query.all()
    count = 0
    for occupancy in expired:
        end_time = occupancy.end_time
        # 处理时区问题
        if end_time.tzinfo is not None:
            end_time = end_time.replace(tzinfo=None)
        if end_time < now:
            db.session.delete(occupancy)
            count += 1
    if count > 0:
        db.session.commit()
    return count
