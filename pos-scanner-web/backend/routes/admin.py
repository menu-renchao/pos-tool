from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import User, DeviceProperty
import functools

admin_bp = Blueprint('admin', __name__)


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


@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    """获取用户列表"""
    status = request.args.get('status')  # pending, approved, rejected, all

    query = User.query
    if status and status != 'all':
        query = query.filter_by(status=status)

    users = query.order_by(User.created_at.desc()).all()
    return jsonify({
        'success': True,
        'users': [u.to_dict() for u in users]
    })


@admin_bp.route('/users/<int:user_id>/approve', methods=['PUT'])
@admin_required
def approve_user(user_id):
    """审核通过用户"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    if user.status == 'approved':
        return jsonify({'success': False, 'error': '用户已通过审核'}), 400

    user.status = 'approved'
    db.session.commit()

    return jsonify({'success': True, 'message': '审核通过'})


@admin_bp.route('/users/<int:user_id>/reject', methods=['PUT'])
@admin_required
def reject_user(user_id):
    """审核拒绝用户"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    if user.status == 'rejected':
        return jsonify({'success': False, 'error': '用户已被拒绝'}), 400

    user.status = 'rejected'
    db.session.commit()

    return jsonify({'success': True, 'message': '已拒绝'})


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['PUT'])
@admin_required
def reset_user_password(user_id):
    """重置用户密码"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    data = request.get_json()
    new_password = data.get('new_password', '')

    if not new_password or len(new_password) < 6:
        return jsonify({'success': False, 'error': '密码至少6个字符'}), 400

    user.set_password(new_password)
    db.session.commit()

    return jsonify({'success': True, 'message': '密码已重置'})


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """删除用户"""
    current_user_id = int(get_jwt_identity())

    if user_id == current_user_id:
        return jsonify({'success': False, 'error': '不能删除自己的账户'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({'success': True, 'message': '用户已删除'})


# ============ 设备性质管理 ============

@admin_bp.route('/device-properties', methods=['GET'])
@admin_required
def get_device_properties():
    """获取所有设备性质"""
    properties = DeviceProperty.query.all()
    return jsonify({
        'success': True,
        'properties': [p.to_dict() for p in properties]
    })


@admin_bp.route('/device-properties', methods=['PUT'])
@admin_required
def set_device_property():
    """设置设备性质（管理员专用）"""
    data = request.get_json()
    merchant_id = data.get('merchant_id')
    property_value = data.get('property')

    if not merchant_id:
        return jsonify({'success': False, 'error': '商家ID不能为空'}), 400

    if not property_value:
        return jsonify({'success': False, 'error': '设备性质不能为空'}), 400

    # 查找或创建
    device_prop = DeviceProperty.query.filter_by(merchant_id=merchant_id).first()
    if device_prop:
        device_prop.property = property_value
    else:
        device_prop = DeviceProperty(merchant_id=merchant_id, property=property_value)
        db.session.add(device_prop)

    db.session.commit()

    return jsonify({
        'success': True,
        'message': '设备性质已更新',
        'property': device_prop.to_dict()
    })


@admin_bp.route('/device-properties/<merchant_id>', methods=['DELETE'])
@admin_required
def delete_device_property(merchant_id):
    """删除设备性质"""
    device_prop = DeviceProperty.query.filter_by(merchant_id=merchant_id).first()
    if not device_prop:
        return jsonify({'success': False, 'error': '设备性质不存在'}), 404

    db.session.delete(device_prop)
    db.session.commit()

    return jsonify({'success': True, 'message': '设备性质已删除'})
