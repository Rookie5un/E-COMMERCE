from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app import db
from app.models import Review, ReviewBatch, Product
from app.models.analysis import ReviewSentiment
from app.services.review_service import ReviewService
from sqlalchemy import or_
import os

bp = Blueprint('reviews', __name__)


@bp.route('/import', methods=['POST'])
@jwt_required()
def import_reviews():
    """导入评论CSV文件或手动输入的评论"""
    try:
        current_user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({'error': '无效的身份令牌'}), 401

    # 检查是文件上传还是手动输入
    if 'file' in request.files:
        # CSV文件上传模式
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400

        # 获取商品ID
        product_id = request.form.get('product_id', type=int)
        if not product_id:
            return jsonify({'error': '商品ID不能为空'}), 400

        # 验证商品存在
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'error': '商品不存在'}), 404

        # 保存文件
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # 创建导入批次
        batch = ReviewBatch(
            product_id=product_id,
            source_type='csv_import',
            file_name=filename,
            status='pending',
            created_by=current_user_id
        )
        db.session.add(batch)
        db.session.commit()

        # 异步处理导入任务
        try:
            review_service = ReviewService()
            result = review_service.import_from_csv(filepath, batch.id)

            return jsonify({
                'message': '导入成功',
                'batch': batch.to_dict(),
                'result': result
            }), 200
        except Exception as e:
            batch.status = 'failed'
            batch.error_message = str(e)
            db.session.commit()
            return jsonify({'error': f'导入失败: {str(e)}'}), 500
    else:
        # 手动输入模式
        data = request.get_json(silent=True) or {}
        product_id = data.get('product_id')
        reviews = data.get('reviews', [])

        # 验证 product_id
        if not product_id:
            return jsonify({'error': '商品ID不能为空'}), 400

        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            return jsonify({'error': '商品ID格式错误'}), 400

        if not isinstance(reviews, list) or len(reviews) == 0:
            return jsonify({'error': '评论列表不能为空'}), 400

        # 验证商品存在
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'error': '商品不存在'}), 404

        # 创建导入批次
        batch = ReviewBatch(
            product_id=product_id,
            source_type='manual_input',
            file_name=f'手动输入_{len(reviews)}条',
            status='pending',
            created_by=current_user_id
        )
        db.session.add(batch)
        db.session.commit()

        # 处理手动输入的评论
        try:
            review_service = ReviewService()
            result = review_service.import_from_list(reviews, batch.id, product_id)

            return jsonify({
                'message': '导入成功',
                'batch': batch.to_dict(),
                'result': result
            }), 200
        except Exception as e:
            batch.status = 'failed'
            batch.error_message = str(e)
            db.session.commit()
            return jsonify({'error': f'导入失败: {str(e)}'}), 500


@bp.route('/batches', methods=['GET'])
@jwt_required()
def get_batches():
    """获取导入批次列表"""
    product_id = request.args.get('product_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    query = ReviewBatch.query
    if product_id:
        query = query.filter_by(product_id=product_id)

    pagination = query.order_by(ReviewBatch.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'batches': [b.to_dict() for b in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200


@bp.route('/batches/<int:batch_id>', methods=['GET'])
@jwt_required()
def get_batch(batch_id):
    """获取批次详情"""
    batch = ReviewBatch.query.get(batch_id)
    if not batch:
        return jsonify({'error': '批次不存在'}), 404

    return jsonify(batch.to_dict()), 200


@bp.route('', methods=['GET'])
@jwt_required()
def get_reviews():
    """获取评论列表"""
    product_id = request.args.get('product_id', type=int)
    batch_id = request.args.get('batch_id', type=int)
    status = request.args.get('status', 'valid')
    sentiment = request.args.get('sentiment')
    keyword = (request.args.get('keyword') or '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    if status not in {'valid', 'deleted', 'all'}:
        return jsonify({'error': 'status参数仅支持 valid / deleted / all'}), 400

    if sentiment and sentiment not in {'positive', 'neutral', 'negative'}:
        return jsonify({'error': 'sentiment参数仅支持 positive / neutral / negative'}), 400

    query = Review.query

    if status == 'valid':
        query = query.filter_by(is_valid=True)
    elif status == 'deleted':
        query = query.filter_by(is_valid=False)

    if product_id:
        query = query.filter_by(product_id=product_id)
    if batch_id:
        query = query.filter_by(batch_id=batch_id)

    # 按情感筛选
    if sentiment:
        # 使用子查询获取每个评论的最新情感分析结果
        from sqlalchemy import func
        subquery = db.session.query(
            ReviewSentiment.review_id,
            func.max(ReviewSentiment.created_at).label('max_created_at')
        ).group_by(ReviewSentiment.review_id).subquery()

        query = query.join(
            ReviewSentiment,
            Review.id == ReviewSentiment.review_id
        ).join(
            subquery,
            (ReviewSentiment.review_id == subquery.c.review_id) &
            (ReviewSentiment.created_at == subquery.c.max_created_at)
        ).filter(ReviewSentiment.label == sentiment)

    if keyword:
        like_pattern = f'%{keyword}%'
        query = query.filter(
            or_(
                Review.raw_content.like(like_pattern),
                Review.cleaned_content.like(like_pattern),
                Review.external_id.like(like_pattern)
            )
        )

    pagination = query.order_by(Review.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'reviews': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200


@bp.route('/<int:review_id>', methods=['GET'])
@jwt_required()
def get_review(review_id):
    """获取评论详情"""
    review = Review.query.get(review_id)
    if not review:
        return jsonify({'error': '评论不存在'}), 404

    return jsonify(review.to_dict()), 200


@bp.route('/<int:review_id>/validity', methods=['PATCH'])
@jwt_required()
def update_review_validity(review_id):
    """更新评论有效性（软删除/恢复）"""
    data = request.get_json(silent=True) or {}
    if 'is_valid' not in data or not isinstance(data.get('is_valid'), bool):
        return jsonify({'error': 'is_valid必须是布尔值'}), 400

    review = Review.query.get(review_id)
    if not review:
        return jsonify({'error': '评论不存在'}), 404

    review.is_valid = data['is_valid']
    db.session.commit()

    return jsonify({
        'message': '更新成功',
        'review': review.to_dict()
    }), 200


@bp.route('/bulk-validity', methods=['POST'])
@jwt_required()
def bulk_update_review_validity():
    """批量更新评论有效性（软删除/恢复）"""
    data = request.get_json(silent=True) or {}
    review_ids = data.get('review_ids')
    is_valid = data.get('is_valid')

    if not isinstance(review_ids, list) or not review_ids:
        return jsonify({'error': 'review_ids必须是非空数组'}), 400
    if not isinstance(is_valid, bool):
        return jsonify({'error': 'is_valid必须是布尔值'}), 400

    normalized_ids = []
    for item in review_ids:
        try:
            normalized_ids.append(int(item))
        except (TypeError, ValueError):
            return jsonify({'error': 'review_ids中存在非法ID'}), 400

    normalized_ids = list(dict.fromkeys(normalized_ids))
    reviews = Review.query.filter(Review.id.in_(normalized_ids)).all()

    found_ids = {review.id for review in reviews}
    missing_ids = [rid for rid in normalized_ids if rid not in found_ids]

    for review in reviews:
        review.is_valid = is_valid
    db.session.commit()

    return jsonify({
        'message': '批量更新成功',
        'updated_count': len(reviews),
        'missing_ids': missing_ids
    }), 200
