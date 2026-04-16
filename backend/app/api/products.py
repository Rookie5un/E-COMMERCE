from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Product, User
from sqlalchemy import or_

bp = Blueprint('products', __name__)


@bp.route('', methods=['GET'])
@jwt_required()
def get_products():
    """获取商品列表"""
    # 获取查询参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    category = request.args.get('category')
    platform = request.args.get('platform')
    keyword = request.args.get('keyword')

    # 构建查询
    query = Product.query

    if category:
        query = query.filter_by(category=category)
    if platform:
        query = query.filter_by(platform=platform)
    if keyword:
        query = query.filter(
            or_(
                Product.name.like(f'%{keyword}%'),
                Product.description.like(f'%{keyword}%')
            )
        )

    # 分页
    pagination = query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'products': [p.to_dict() for p in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200


@bp.route('/<int:product_id>', methods=['GET'])
@jwt_required()
def get_product(product_id):
    """获取商品详情"""
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': '商品不存在'}), 404

    return jsonify(product.to_dict()), 200


@bp.route('', methods=['POST'])
@jwt_required()
def create_product():
    """创建商品"""
    try:
        current_user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({'error': '无效的身份令牌'}), 401

    data = request.get_json()

    # 验证必填字段
    if not data.get('name') or not data.get('category') or not data.get('platform'):
        return jsonify({'error': '商品名称、品类和平台不能为空'}), 400

    product = Product(
        name=data['name'],
        category=data['category'],
        platform=data['platform'],
        url=data.get('url'),
        description=data.get('description'),
        created_by=current_user_id
    )

    db.session.add(product)
    db.session.commit()

    return jsonify({
        'message': '商品创建成功',
        'product': product.to_dict()
    }), 201


@bp.route('/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    """更新商品"""
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': '商品不存在'}), 404

    data = request.get_json()

    if 'name' in data:
        product.name = data['name']
    if 'category' in data:
        product.category = data['category']
    if 'platform' in data:
        product.platform = data['platform']
    if 'url' in data:
        product.url = data['url']
    if 'description' in data:
        product.description = data['description']

    db.session.commit()

    return jsonify({
        'message': '商品更新成功',
        'product': product.to_dict()
    }), 200


@bp.route('/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    """删除商品"""
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': '商品不存在'}), 404

    db.session.delete(product)
    db.session.commit()

    return jsonify({'message': '商品删除成功'}), 200


@bp.route('/categories', methods=['GET'])
@jwt_required()
def get_categories():
    """获取所有品类"""
    categories = db.session.query(Product.category).distinct().all()
    return jsonify({
        'categories': [c[0] for c in categories]
    }), 200


@bp.route('/platforms', methods=['GET'])
@jwt_required()
def get_platforms():
    """获取所有平台"""
    platforms = db.session.query(Product.platform).distinct().all()
    return jsonify({
        'platforms': [p[0] for p in platforms]
    }), 200
