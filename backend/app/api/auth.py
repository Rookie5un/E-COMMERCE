from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import User
from datetime import datetime

bp = Blueprint('auth', __name__)


def _parse_current_user_id():
    """JWT identity 统一按字符串存储，业务层按整数用户ID使用。"""
    identity = get_jwt_identity()
    try:
        return int(identity)
    except (TypeError, ValueError):
        return None


@bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()

    # 验证必填字段
    if not data.get('username') or not data.get('password'):
        return jsonify({'error': '用户名和密码不能为空'}), 400

    # 检查用户名是否已存在
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': '用户名已存在'}), 400

    # 创建新用户
    user = User(
        username=data['username'],
        password=generate_password_hash(data['password']),
        email=data.get('email'),
        real_name=data.get('real_name'),
        role=data.get('role', 'analyst')
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({
        'message': '注册成功',
        'user': user.to_dict()
    }), 201


@bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()

    if not data.get('username') or not data.get('password'):
        return jsonify({'error': '用户名和密码不能为空'}), 400

    user = User.query.filter_by(username=data['username']).first()

    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'error': '用户名或密码错误'}), 401

    if user.status != 'active':
        return jsonify({'error': '账号已被禁用'}), 403

    # 更新最后登录时间
    user.last_login_at = datetime.utcnow()
    db.session.commit()

    # 生成token
    # PyJWT 2.12+ 要求 sub 必须是字符串
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }), 200


@bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """刷新token"""
    current_user_id = _parse_current_user_id()
    if current_user_id is None:
        return jsonify({'error': '无效的身份令牌'}), 401

    access_token = create_access_token(identity=str(current_user_id))
    return jsonify({'access_token': access_token}), 200


@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """获取当前用户信息"""
    current_user_id = _parse_current_user_id()
    if current_user_id is None:
        return jsonify({'error': '无效的身份令牌'}), 401

    user = User.query.get(current_user_id)

    if not user:
        return jsonify({'error': '用户不存在'}), 404

    return jsonify(user.to_dict()), 200


@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """用户登出"""
    # JWT是无状态的，登出主要在前端清除token
    return jsonify({'message': '登出成功'}), 200
