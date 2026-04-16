from datetime import datetime
import threading

from flask import Blueprint, current_app, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, desc

from app import db
from app.models import Product, ReviewBatch, Review
from app.models.analysis import AnalysisRun, ReviewSentiment, AspectMention, IssueTopic
from app.services.summary_utils import build_sentiment_distribution

bp = Blueprint('analysis', __name__)

VALID_RUN_STATUSES = {'pending', 'running', 'completed', 'failed', 'canceled'}
CANCELABLE_RUN_STATUSES = {'pending', 'running'}
RETRYABLE_RUN_STATUSES = {'failed', 'canceled'}


def _parse_current_user_id():
    identity = get_jwt_identity()
    try:
        return int(identity)
    except (TypeError, ValueError):
        return None


def _start_analysis_thread(run_id: int):
    """启动后台线程执行分析（生产环境建议使用Celery）"""
    if current_app.config.get('TESTING'):
        return

    def run_analysis_task(target_run_id: int):
        from app import create_app

        app = create_app()
        with app.app_context():
            try:
                # 延迟导入，避免在未安装可选 NLP 依赖时阻塞服务启动
                from app.services.analysis_service import AnalysisService

                service = AnalysisService()
                service.run_analysis(target_run_id)
            except Exception as e:
                print(f'分析任务失败: {str(e)}')

    thread = threading.Thread(target=run_analysis_task, args=(run_id,))
    thread.daemon = True
    thread.start()


def _ensure_run_id_for_testing(run: AnalysisRun):
    """SQLite 测试环境下，BigInteger 主键不会自动递增，需手动赋值。"""
    if not current_app.config.get('TESTING'):
        return
    if db.engine.dialect.name != 'sqlite':
        return
    if run.id is not None:
        return

    max_id = db.session.query(func.max(AnalysisRun.id)).scalar() or 0
    run.id = int(max_id) + 1


@bp.route('/run', methods=['POST'])
@jwt_required()
def create_analysis_run():
    """创建分析任务"""
    current_user_id = _parse_current_user_id()
    if current_user_id is None:
        return jsonify({'error': '无效的身份令牌'}), 401

    data = request.get_json(silent=True) or {}

    product_id = data.get('product_id')
    if not product_id:
        return jsonify({'error': '商品ID不能为空'}), 400

    try:
        product_id = int(product_id)
    except (TypeError, ValueError):
        return jsonify({'error': '商品ID格式错误'}), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': '商品不存在'}), 404

    batch_id = data.get('batch_id')
    if batch_id is not None:
        try:
            batch_id = int(batch_id)
        except (TypeError, ValueError):
            return jsonify({'error': '批次ID格式错误'}), 400

        batch = ReviewBatch.query.get(batch_id)
        if not batch:
            return jsonify({'error': '批次不存在'}), 404
        if batch.product_id != product_id:
            return jsonify({'error': '批次不属于当前商品'}), 400

    # 检查是否有评论数据
    review_query = Review.query.filter_by(
        product_id=product_id,
        is_valid=True
    )
    if batch_id is not None:
        review_query = review_query.filter_by(batch_id=batch_id)

    if review_query.count() == 0:
        return jsonify({'error': '该商品暂无评论数据，请先导入评论'}), 400

    run = AnalysisRun(
        product_id=product_id,
        batch_id=batch_id,
        model_name=data.get('model_name', current_app.config['SENTIMENT_MODEL']),
        model_version=data.get('model_version', current_app.config['SENTIMENT_MODEL_VERSION']),
        config_json=data.get('config'),
        started_by=current_user_id,
        status='pending',
        progress_stage='queued',
        progress_message='任务排队中',
        progress_updated_at=datetime.utcnow(),
    )

    _ensure_run_id_for_testing(run)
    db.session.add(run)
    db.session.commit()

    _start_analysis_thread(run.id)

    return jsonify({
        'message': '分析任务已创建并开始执行',
        'run': run.to_dict()
    }), 201


@bp.route('/runs', methods=['GET'])
@jwt_required()
def get_analysis_runs():
    """获取分析任务列表"""
    product_id = request.args.get('product_id', type=int)
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    if status and status not in VALID_RUN_STATUSES:
        return jsonify({'error': 'status参数无效'}), 400

    query = AnalysisRun.query
    if product_id:
        query = query.filter_by(product_id=product_id)
    if status:
        query = query.filter_by(status=status)

    pagination = query.order_by(AnalysisRun.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'runs': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200


@bp.route('/runs/<int:run_id>', methods=['GET'])
@jwt_required()
def get_analysis_run(run_id):
    """获取分析任务详情"""
    run = AnalysisRun.query.get(run_id)
    if not run:
        return jsonify({'error': '分析任务不存在'}), 404

    return jsonify(run.to_dict()), 200


@bp.route('/runs/<int:run_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_analysis_run(run_id):
    """取消分析任务"""
    run = AnalysisRun.query.get(run_id)
    if not run:
        return jsonify({'error': '分析任务不存在'}), 404

    if run.status not in CANCELABLE_RUN_STATUSES:
        return jsonify({'error': f'当前状态 {run.status} 不可取消'}), 400

    run.status = 'canceled'
    run.error_message = '任务已取消'
    run.progress_stage = 'canceled'
    run.progress_message = '任务已取消'
    run.progress_updated_at = datetime.utcnow()
    run.finished_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'message': '分析任务已取消',
        'run': run.to_dict()
    }), 200


@bp.route('/runs/<int:run_id>/retry', methods=['POST'])
@jwt_required()
def retry_analysis_run(run_id):
    """重试分析任务"""
    current_user_id = _parse_current_user_id()
    if current_user_id is None:
        return jsonify({'error': '无效的身份令牌'}), 401

    run = AnalysisRun.query.get(run_id)
    if not run:
        return jsonify({'error': '分析任务不存在'}), 404

    if run.status not in RETRYABLE_RUN_STATUSES:
        return jsonify({'error': f'当前状态 {run.status} 不支持重试'}), 400

    review_query = Review.query.filter_by(product_id=run.product_id, is_valid=True)
    if run.batch_id:
        review_query = review_query.filter_by(batch_id=run.batch_id)
    if review_query.count() == 0:
        return jsonify({'error': '没有可用于重试的有效评论'}), 400

    retry_run = AnalysisRun(
        product_id=run.product_id,
        batch_id=run.batch_id,
        model_name=run.model_name,
        model_version=run.model_version,
        config_json=run.config_json,
        started_by=current_user_id,
        status='pending',
        progress_stage='queued',
        progress_message='重试任务排队中',
        progress_updated_at=datetime.utcnow(),
    )
    _ensure_run_id_for_testing(retry_run)
    db.session.add(retry_run)
    db.session.commit()

    _start_analysis_thread(retry_run.id)

    return jsonify({
        'message': '重试任务已创建并开始执行',
        'source_run_id': run.id,
        'run': retry_run.to_dict()
    }), 201


@bp.route('/summary', methods=['GET'])
@jwt_required()
def get_analysis_summary():
    """获取分析总览"""
    product_id = request.args.get('product_id', type=int)
    run_id = request.args.get('run_id', type=int)

    if not product_id and not run_id:
        return jsonify({'error': '需要提供product_id或run_id'}), 400

    # 获取最新的分析任务
    if product_id and not run_id:
        run = AnalysisRun.query.filter_by(
            product_id=product_id,
            status='completed'
        ).order_by(AnalysisRun.finished_at.desc()).first()

        if not run:
            return jsonify({'error': '该商品暂无完成的分析任务'}), 404
        run_id = run.id

    # 统计情感分布
    sentiment_stats = db.session.query(
        ReviewSentiment.label,
        func.count(ReviewSentiment.id).label('count'),
        func.avg(ReviewSentiment.confidence).label('avg_confidence')
    ).filter_by(run_id=run_id).group_by(ReviewSentiment.label).all()

    sentiment_distribution, total_reviews = build_sentiment_distribution(sentiment_stats)

    # 统计功能点
    aspect_stats = db.session.query(
        AspectMention.normalized_aspect,
        func.count(AspectMention.id).label('count')
    ).filter_by(run_id=run_id).group_by(
        AspectMention.normalized_aspect
    ).order_by(desc('count')).limit(10).all()

    # 统计问题关键词
    issue_stats = db.session.query(
        IssueTopic.normalized_keyword,
        IssueTopic.frequency
    ).filter_by(run_id=run_id).order_by(
        desc(IssueTopic.frequency)
    ).limit(10).all()

    return jsonify({
        'run_id': run_id,
        'total_reviews': total_reviews,
        'sentiment_distribution': sentiment_distribution,
        'top_aspects': [{'aspect': a[0], 'count': a[1]} for a in aspect_stats],
        'top_issues': [{'keyword': i[0], 'frequency': i[1]} for i in issue_stats]
    }), 200


@bp.route('/sentiment', methods=['GET'])
@jwt_required()
def get_sentiment_analysis():
    """获取情感分析结果"""
    run_id = request.args.get('run_id', type=int)
    if not run_id:
        return jsonify({'error': 'run_id不能为空'}), 400

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = ReviewSentiment.query.filter_by(run_id=run_id)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'sentiments': [s.to_dict() for s in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200


@bp.route('/aspects', methods=['GET'])
@jwt_required()
def get_aspect_analysis():
    """获取功能点分析结果"""
    run_id = request.args.get('run_id', type=int)
    if not run_id:
        return jsonify({'error': 'run_id不能为空'}), 400

    aspect = request.args.get('aspect')

    query = AspectMention.query.filter_by(run_id=run_id)
    if aspect:
        query = query.filter_by(normalized_aspect=aspect)

    aspects = query.all()

    return jsonify({
        'aspects': [a.to_dict() for a in aspects],
        'total': len(aspects)
    }), 200


@bp.route('/issues', methods=['GET'])
@jwt_required()
def get_issue_analysis():
    """获取负面问题分析结果"""
    run_id = request.args.get('run_id', type=int)
    if not run_id:
        return jsonify({'error': 'run_id不能为空'}), 400

    issues = IssueTopic.query.filter_by(run_id=run_id).order_by(
        desc(IssueTopic.frequency)
    ).all()

    return jsonify({
        'issues': [i.to_dict() for i in issues],
        'total': len(issues)
    }), 200
