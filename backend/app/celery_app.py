"""
Celery application configuration.

Celery is an optional runtime dependency for the backend. Importing this module
must not break the Flask app when requirements-extras.txt has not been installed.
"""

import os

try:
    from celery import Celery
except ImportError:  # pragma: no cover - depends on optional dependency install
    Celery = None


DEFAULT_BROKER_URL = 'redis://localhost:6379/0'
DEFAULT_RESULT_BACKEND = 'redis://localhost:6379/0'
DEFAULT_QUEUE_NAME = 'analysis'


celery = Celery('ecommerce_review_analysis') if Celery is not None else None


def _read_config(app, key: str, env_key: str, default: str):
    if app is not None:
        return app.config.get(key, default)
    return os.getenv(env_key, default)


def configure_celery(app=None):
    """Configure and return the shared Celery instance."""
    if celery is None:
        raise RuntimeError('Celery is not installed. Run: pip install -r requirements-extras.txt')

    queue_name = _read_config(app, 'ANALYSIS_QUEUE_NAME', 'ANALYSIS_QUEUE_NAME', DEFAULT_QUEUE_NAME)

    celery.conf.update(
        broker_url=_read_config(app, 'CELERY_BROKER_URL', 'CELERY_BROKER_URL', DEFAULT_BROKER_URL),
        result_backend=_read_config(
            app,
            'CELERY_RESULT_BACKEND',
            'CELERY_RESULT_BACKEND',
            DEFAULT_RESULT_BACKEND,
        ),
        task_default_queue=queue_name,
        task_routes={
            'analysis.run': {'queue': queue_name},
        },
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        enable_utc=True,
        timezone='UTC',
        broker_connection_retry_on_startup=True,
        task_publish_retry=False,
        imports=('app.tasks.analysis_tasks',),
    )
    return celery


if celery is not None:
    configure_celery()
