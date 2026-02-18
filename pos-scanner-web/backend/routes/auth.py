from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)
from extensions import db
from models import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()

    username = data.get('username', '').strip()
    password = data.get('password', '')
    email = data.get('email', '').strip()

    # 验证输入
    if not username or not password or not email:
        return jsonify({'success': False, 'error': '所有字段都必填'}), 400

    if len(username) < 3:
        return jsonify({'success': False, 'error': '用户名至少3个字符'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'error': '密码至少6个字符'}), 400

    # 检查用户名是否存在
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'error': '用户名已存在'}), 400

    # 检查邮箱是否存在
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': '邮箱已被注册'}), 400

    # 创建用户
    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '注册成功，请等待管理员审核'
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'success': False, 'error': '用户名和密码必填'}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({'success': False, 'error': '用户名或密码错误'}), 401

    if user.status != 'approved':
        return jsonify({'success': False, 'error': '账户尚未通过审核'}), 403

    # 创建 Token (identity 必须是字符串)
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        'success': True,
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    })


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """用户登出"""
    # JWT 无状态，客户端删除 Token 即可
    return jsonify({'success': True, 'message': '登出成功'})


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    """获取当前用户信息"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    return jsonify({'success': True, 'user': user.to_dict()})


@auth_bp.route('/password', methods=['PUT'])
@jwt_required()
def change_password():
    """修改密码"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    data = request.get_json()
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({'success': False, 'error': '旧密码和新密码必填'}), 400

    if not user.check_password(old_password):
        return jsonify({'success': False, 'error': '旧密码错误'}), 400

    if len(new_password) < 6:
        return jsonify({'success': False, 'error': '新密码至少6个字符'}), 400

    user.set_password(new_password)
    db.session.commit()

    return jsonify({'success': True, 'message': '密码修改成功'})
