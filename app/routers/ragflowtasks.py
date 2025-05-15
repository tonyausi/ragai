import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from celery.result import AsyncResult  # Import AsyncResult
from app.tasks.process_task import process_excel  # Import the Celery task
from app.tasks.celery_worker import celery_app  # Import the Celery app
from app.models.task_schemas import TaskResult, TaskStatus


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/ragflowai",
    tags=["ragflowai"],
    responses={404: {"description": "Not found"}},
)


# add heartbeat endpoint to check if the server is running
@router.get("/heartbeat")
async def heartbeat():
    # check if redis is running
    try:
        celery_app.control.ping(timeout=1)
        logger.info("Redis is running")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Redis is not running: {e}")
        raise HTTPException(status_code=500, detail="Redis is not running")


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    filename = file.filename
    logger.info(f"For RagFlow AI, input file.filename: {filename}")
    contents = await file.read()
    task = process_excel.delay(filename, contents)  # Pass the file contents to the task
    return {"task_id": task.id}


@router.get("/status/{task_id}", response_model=TaskResult)
async def get_status(task_id: str):
    # check if the task_id can be found in the Redis database
    if not task_id:
        err_msg = f"Task ID {task_id} is not valid"
        logger.error(err_msg)
        raise HTTPException(status_code=403, detail=err_msg)

    # Use AsyncResult with the Celery app instance
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        logger.info(f"Task task_result.state: {task_result.state}")
        logger.info(f"Task task_result.info: {task_result.info}")
        if task_result.state == TaskStatus.PENDING:
            err_msg = f"Task ID: {task_id} not found in Redis or has expired"
            logger.error(err_msg)
            raise HTTPException(status_code=404, detail=err_msg)
    except Exception as e:
        err_msg = f"Task ID: {task_id} query failed with error: {e}"
        logger.error(err_msg)
        raise HTTPException(status_code=404, detail=err_msg)
    # if the task state is FAILURE, return TaskResult with FAILURE status and make progress 0
    if task_result.state == TaskStatus.FAILURE:
        return TaskResult(
            task_id=task_id,
            status=TaskStatus.FAILURE,
            progress=0,
            error="Task failed",
        )
    else:
        return TaskResult(
            task_id=task_id,
            status=task_result.state if task_result.state else "UNKNOWN",
            progress=task_result.info.get("progress", 0) if task_result.info else 0,
            filename=task_result.info.get("filename", None),
            processed_at=task_result.info.get("processed_at", None),
        )


# add get endpoint to download the processed file
@router.get("/download/{task_id}", response_class=FileResponse)
async def download_file(task_id: str):
    # Use AsyncResult with the Celery app instance
    task_result = AsyncResult(task_id, app=celery_app)

    if not task_result:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check if the task is completed and has a result
    if task_result.state != "SUCCESS":
        raise HTTPException(status_code=400, detail="Task is not completed or failed")

    # Get the info mata from the task
    result = task_result.info
    logger.info(f"For download API, Task task_result.info: {task_result.info}")

    # Check if the result contains a download path
    if not result or "download_path" not in result:
        raise HTTPException(status_code=400, detail="No file available for download")

    file_path = result["download_path"]
    logger.info(f"For download API, file_path: {file_path}")

    headers = {
        "Content-Disposition": "attachment; filename=SeismaResponse.xlsx",
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    try:
        return FileResponse(
            path=file_path,
            headers=headers,
            media_type=headers["Content-Type"],
        )
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail="Error downloading file")
