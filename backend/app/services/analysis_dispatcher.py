"""
Analysis task dispatcher.

API routes create AnalysisRun rows; this module decides how that run is executed.
The database remains the source of truth for status and progress.
"""

from dataclasses import dataclass
from datetime import datetime
import logging
import threading

from flask import current_app

from app import db
from app.models.analysis import AnalysisRun

logger = logging.getLogger(__name__)


class AnalysisDispatchError(RuntimeError):
    """Raised when an analysis task cannot be dispatched."""


@dataclass
class AnalysisDispatchResult:
    backend: str
    task_id: str | None = None
    fallback_used: bool = False
    error: str | None = None


def dispatch_analysis_run(run_id: int) -> AnalysisDispatchResult:
    """Dispatch one AnalysisRun to the configured execution backend."""
    if current_app.config.get('TESTING'):
        logger.info('Testing mode: skip dispatch for analysis run %s', run_id)
        return AnalysisDispatchResult(backend='testing')

    backend = str(current_app.config.get('ANALYSIS_TASK_BACKEND', 'celery')).strip().lower()

    if backend == 'thread':
        _start_analysis_thread(run_id)
        return AnalysisDispatchResult(backend='thread')

    if backend != 'celery':
        exc = AnalysisDispatchError(f'Unsupported ANALYSIS_TASK_BACKEND: {backend}')
        _mark_dispatch_failed(run_id, exc)
        raise exc

    try:
        async_result = _enqueue_celery_run(run_id)
        return AnalysisDispatchResult(
            backend='celery',
            task_id=getattr(async_result, 'id', None),
        )
    except Exception as exc:
        logger.warning('Celery dispatch failed for analysis run %s: %s', run_id, exc)
        if _thread_fallback_enabled():
            _start_analysis_thread(run_id)
            return AnalysisDispatchResult(
                backend='thread',
                fallback_used=True,
                error=str(exc),
            )

        dispatch_error = exc if isinstance(exc, AnalysisDispatchError) else AnalysisDispatchError(str(exc))
        _mark_dispatch_failed(run_id, dispatch_error)
        raise dispatch_error


def _enqueue_celery_run(run_id: int):
    try:
        from app.tasks.analysis_tasks import run_analysis_task
    except ImportError as exc:
        raise AnalysisDispatchError(
            'Celery task module could not be imported. Run: pip install -r requirements-extras.txt'
        ) from exc

    queue_name = current_app.config.get('ANALYSIS_QUEUE_NAME', 'analysis')
    return run_analysis_task.apply_async(args=[int(run_id)], queue=queue_name)


def _start_analysis_thread(run_id: int):
    """Fallback executor used when Celery is disabled or unavailable."""

    def run_analysis_task(target_run_id: int):
        from app import create_app

        app = create_app()
        with app.app_context():
            try:
                from app.services.analysis_service import AnalysisService

                service = AnalysisService()
                service.run_analysis(target_run_id)
            except Exception:
                logger.exception('Thread fallback failed for analysis run %s', target_run_id)

    thread = threading.Thread(target=run_analysis_task, args=(int(run_id),))
    thread.daemon = True
    thread.start()


def _thread_fallback_enabled() -> bool:
    value = current_app.config.get('ANALYSIS_THREAD_FALLBACK', True)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _mark_dispatch_failed(run_id: int, exc: Exception):
    run = db.session.get(AnalysisRun, int(run_id))
    if not run:
        return

    now = datetime.utcnow()
    run.status = 'failed'
    run.error_message = f'任务投递失败: {exc}'
    run.finished_at = now
    run.progress_stage = 'failed'
    run.progress_message = run.error_message
    run.progress_updated_at = now
    db.session.commit()
