from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_migrate import Migrate
from sqlalchemy import inspect, text
from config import config
import os

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()


def _ensure_analysis_progress_columns(app):
    """
    兼容性兜底：
    若数据库中 analysis_runs 缺少阶段字段，自动补齐，避免接口500。
    """
    try:
        inspector = inspect(db.engine)
        if 'analysis_runs' not in inspector.get_table_names():
            return

        existing_columns = {col['name'] for col in inspector.get_columns('analysis_runs')}
        missing_columns = []
        if 'progress_stage' not in existing_columns:
            missing_columns.append('progress_stage')
        if 'progress_message' not in existing_columns:
            missing_columns.append('progress_message')
        if 'progress_updated_at' not in existing_columns:
            missing_columns.append('progress_updated_at')

        if not missing_columns:
            return

        dialect = db.engine.dialect.name
        with db.engine.begin() as conn:
            if dialect == 'mysql':
                clauses = []
                if 'progress_stage' in missing_columns:
                    clauses.append('ADD COLUMN progress_stage VARCHAR(50) NULL AFTER status')
                if 'progress_message' in missing_columns:
                    clauses.append('ADD COLUMN progress_message TEXT NULL AFTER progress_stage')
                if 'progress_updated_at' in missing_columns:
                    clauses.append('ADD COLUMN progress_updated_at DATETIME NULL AFTER progress_message')
                conn.execute(text(f"ALTER TABLE analysis_runs {', '.join(clauses)}"))
            else:
                # SQLite / 其他方言兜底，不使用 AFTER 语法
                if 'progress_stage' in missing_columns:
                    conn.execute(text('ALTER TABLE analysis_runs ADD COLUMN progress_stage VARCHAR(50)'))
                if 'progress_message' in missing_columns:
                    conn.execute(text('ALTER TABLE analysis_runs ADD COLUMN progress_message TEXT'))
                if 'progress_updated_at' in missing_columns:
                    conn.execute(text('ALTER TABLE analysis_runs ADD COLUMN progress_updated_at DATETIME'))

            conn.execute(text("""
                UPDATE analysis_runs
                SET
                  progress_stage = COALESCE(progress_stage, status),
                  progress_message = COALESCE(
                    progress_message,
                    CASE
                      WHEN status = 'pending' THEN '任务排队中'
                      WHEN status = 'running' THEN '任务执行中'
                      WHEN status = 'completed' THEN '分析任务已完成'
                      WHEN status = 'failed' THEN COALESCE(error_message, '任务失败')
                      WHEN status = 'canceled' THEN '任务已取消'
                      ELSE NULL
                    END
                  ),
                  progress_updated_at = COALESCE(progress_updated_at, finished_at, started_at, created_at)
                WHERE progress_stage IS NULL OR progress_message IS NULL OR progress_updated_at IS NULL
            """))

        app.logger.info('已自动补齐 analysis_runs 任务阶段字段: %s', ', '.join(missing_columns))
    except Exception as exc:
        app.logger.warning('自动补齐 analysis_runs 阶段字段失败: %s', exc)


def create_app(config_name=None):
    """应用工厂函数"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # 初始化扩展
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app, origins=app.config['CORS_ORIGINS'])

    with app.app_context():
        _ensure_analysis_progress_columns(app)

    # 确保必要的目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['REPORT_FOLDER'], exist_ok=True)
    os.makedirs(app.config['MODEL_FOLDER'], exist_ok=True)

    # 注册蓝图
    from app.api import auth, products, reviews, analysis, reports
    app.register_blueprint(auth.bp, url_prefix='/api/auth')
    app.register_blueprint(products.bp, url_prefix='/api/products')
    app.register_blueprint(reviews.bp, url_prefix='/api/reviews')
    app.register_blueprint(analysis.bp, url_prefix='/api/analysis')
    app.register_blueprint(reports.bp, url_prefix='/api/reports')

    # 健康检查端点
    @app.route('/health')
    def health():
        return {'status': 'ok'}

    return app
