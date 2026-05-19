#!/usr/bin/env python3
"""
Celery worker entrypoint.

Run from backend/:
celery -A celery_worker.celery worker -Q analysis --loglevel=info --concurrency=1
"""

import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'), override=True)

from app.celery_app import configure_celery  # noqa: E402
import app.tasks.analysis_tasks  # noqa: E402,F401

celery = configure_celery()
