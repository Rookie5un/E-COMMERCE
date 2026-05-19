"""
Celery tasks for analysis runs.
"""

import logging

from app.celery_app import celery

logger = logging.getLogger(__name__)


def _execute_analysis_run(run_id: int):
    from app import create_app

    app = create_app()
    with app.app_context():
        from app.services.analysis_service import AnalysisService

        service = AnalysisService()
        service.run_analysis(int(run_id))
    return {'run_id': int(run_id)}


if celery is not None:

    @celery.task(name='analysis.run', bind=True)
    def run_analysis_task(self, run_id: int):
        logger.info('Celery worker received analysis run %s', run_id)
        return _execute_analysis_run(run_id)

else:

    class _UnavailableAnalysisTask:
        name = 'analysis.run'

        def apply_async(self, *args, **kwargs):
            raise RuntimeError('Celery is not installed. Run: pip install -r requirements-extras.txt')

    run_analysis_task = _UnavailableAnalysisTask()
