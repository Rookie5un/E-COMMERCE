from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity

from app import db
from app.models import User


def get_current_user():
    """Return the active user represented by the current JWT identity."""
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None

    user = db.session.get(User, user_id)
    if not user or user.status != 'active':
        return None
    return user


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return jsonify({'error': '无效的身份令牌'}), 401
        if user.role != 'admin':
            return jsonify({'error': '没有权限访问'}), 403
        return fn(*args, **kwargs)

    return wrapper
