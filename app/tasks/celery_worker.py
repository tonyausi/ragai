# app/tasks/celery_worker.py
import os
import logging
from celery import Celery
from celery.signals import after_setup_logger, after_setup_task_logger
from app.config.setting import settings
from app.config.logging_config import load_logging_config


# Load logging configuration from a YAML file
base_dir = os.path.dirname(os.path.abspath(__file__))
CELERY_LOGGING_CONFIG = load_logging_config(
    os.path.join(base_dir, "../config/logging_celery.yaml")
)


@after_setup_logger.connect
def setup_celery_logger(logger, *args, **kwargs):
    logging.config.dictConfig(CELERY_LOGGING_CONFIG)


@after_setup_task_logger.connect
def setup_task_logger(logger, *args, **kwargs):
    logging.config.dictConfig(CELERY_LOGGING_CONFIG)


# Initialize the Celery app with Redis as the broker/backend
celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.process_task"],  # Include your task module
)

# Optional: Configure task settings
celery_app.conf.update(task_track_started=True, result_extended=True)

celery_worker_logger = logging.getLogger("celery")
celery_worker_logger.info(
    "RAG AI Worker started"
)  # Goes to handlers for 'celery' (console + celery.log) :contentReference[oaicite:1]{index=1}
