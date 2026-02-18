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


@admin_bp.route('/users', methods=['POST'])
@admin_required
def create_user():
    """创建用户（管理员）"""
    data = request.get_json()

    username = data.get('username', '').strip()
    password = data.get('password', '')
    email = data.get('email', '').strip()
    role = data.get('role', 'user')
    status = data.get('status', 'approved')  # 管理员创建的用户默认已通过

    # 验证
    if not username or not password or not email:
        return jsonify({'success': False, 'error': '用户名、密码、邮箱都必填'}), 400

    if len(username) < 3:
        return jsonify({'success': False, 'error': '用户名至少3个字符'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'error': '密码至少6个字符'}), 400

    if role not in ['user', 'admin']:
        return jsonify({'success': False, 'error': '角色只能是 user 或 admin'}), 400

    # 检查重复
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'error': '用户名已存在'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': '邮箱已被使用'}), 400

    # 创建用户
    user = User(username=username, email=email, role=role, status=status)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '用户创建成功',
        'user': user.to_dict()
    }), 201


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """更新用户信息（管理员）"""
    current_user_id = int(get_jwt_identity())

    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    data = request.get_json()

    # 更新用户名
    if 'username' in data:
        new_username = data['username'].strip()
        if new_username and new_username != user.username:
            if User.query.filter(User.username == new_username, User.id != user_id).first():
                return jsonify({'success': False, 'error': '用户名已存在'}), 400
            user.username = new_username

    # 更新邮箱
    if 'email' in data:
        new_email = data['email'].strip()
        if new_email and new_email != user.email:
            if User.query.filter(User.email == new_email, User.id != user_id).first():
                return jsonify({'success': False, 'error': '邮箱已被使用'}), 400
            user.email = new_email

    # 更新角色
    if 'role' in data:
        new_role = data['role']
        if new_role not in ['user', 'admin']:
            return jsonify({'success': False, 'error': '角色只能是 user 或 admin'}), 400
        # 防止管理员取消自己的管理员权限
        if user_id == current_user_id and new_role != 'admin':
            return jsonify({'success': False, 'error': '不能取消自己的管理员权限'}), 400
        user.role = new_role

    # 更新状态
    if 'status' in data:
        new_status = data['status']
        if new_status not in ['pending', 'approved', 'rejected']:
            return jsonify({'success': False, 'error': '无效的状态'}), 400
        user.status = new_status

    db.session.commit()

    return jsonify({
        'success': True,
        'message': '用户信息已更新',
        'user': user.to_dict()
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
