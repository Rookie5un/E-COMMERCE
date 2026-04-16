from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.analysis import Report, AnalysisRun
from app.services.report_service import ReportService
import os

bp = Blueprint('reports', __name__)


@bp.route('', methods=['POST'])
@jwt_required()
def create_report():
    """生成分析报告"""
    try:
        current_user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({'error': '无效的身份令牌'}), 401

    data = request.get_json(silent=True) or {}

    run_id = data.get('run_id')
    if not run_id:
        return jsonify({'error': '分析任务ID不能为空'}), 400
    try:
        run_id = int(run_id)
    except (TypeError, ValueError):
        return jsonify({'error': '分析任务ID格式错误'}), 400

    run = AnalysisRun.query.get(run_id)
    if not run:
        return jsonify({'error': '分析任务不存在'}), 404

    if run.status != 'completed':
        return jsonify({'error': '分析任务未完成'}), 400

    # 生成报告
    try:
        report_service = ReportService()
        report = report_service.generate_report(run_id, current_user_id)

        return jsonify({
            'message': '报告生成成功',
            'report': report.to_dict()
        }), 201
    except Exception as e:
        return jsonify({'error': f'报告生成失败: {str(e)}'}), 500


@bp.route('', methods=['GET'])
@jwt_required()
def get_reports():
    """获取报告列表"""
    run_id = request.args.get('run_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    query = Report.query
    if run_id:
        query = query.filter_by(run_id=run_id)

    pagination = query.order_by(Report.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'reports': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200


@bp.route('/<int:report_id>', methods=['GET'])
@jwt_required()
def get_report(report_id):
    """获取报告详情"""
    report = Report.query.get(report_id)
    if not report:
        return jsonify({'error': '报告不存在'}), 404

    return jsonify(report.to_dict()), 200


@bp.route('/<int:report_id>/download', methods=['GET'])
@jwt_required()
def download_report(report_id):
    """下载报告PDF"""
    report = Report.query.get(report_id)
    if not report:
        return jsonify({'error': '报告不存在'}), 404

    if not report.pdf_path or not os.path.exists(report.pdf_path):
        return jsonify({'error': 'PDF文件不存在'}), 404

    return send_file(
        report.pdf_path,
        as_attachment=True,
        download_name=f'{report.title}.pdf'
    )
