from pydantic import BaseModel
from typing import Optional
from enum import Enum
from datetime import datetime
from celery import states


class TaskStatus(str, Enum):
    PENDING = states.PENDING
    STARTED = states.STARTED
    SUCCESS = states.SUCCESS
    FAILURE = states.FAILURE
    REVOKED = states.REVOKED
    RETRY = states.RETRY
    IGNORED = states.IGNORED
    PROCESSING = "PROCESSING"  # Custom status for processing tasks
    ERRORED = "ERROR"  # Custom status for error tasks


class TaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    progress: float = 0.0
    download_path: Optional[str] = None  # Path to generated Excel file
    error: Optional[str] = None
    filename: Optional[str] = None  # Original uploaded filename
    processed_at: Optional[datetime] = None
