import os
import asyncio
import logging
from celery import Celery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CeleryWorker")

# Retrieve Redis configuration from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery app
celery_app = Celery(
    "sarkariswarm",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Make sure we don't have issues with Windows event loops
    worker_max_tasks_per_child=100
)

@celery_app.task(name="celery_worker.run_apply_task")
def run_apply_task(task_id: str, user_data: dict, exam_data: dict):
    """
    Celery task wrapper to execute ApplyService.run_application in a separate process.
    Runs the asynchronous event loop for the Playwright worker.
    """
    logger.info(f"Starting Celery task run_apply_task for task_id: {task_id}")
    
    from database.db import AsyncSessionLocal
    from services.apply_service import ApplyService
    
    async def execute():
        async with AsyncSessionLocal() as session:
            await ApplyService.run_application(task_id, user_data, exam_data, session)
            
    # Run the async loop inside the synchronous Celery worker thread/process
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(execute())
        logger.info(f"Successfully completed run_apply_task for task_id: {task_id}")
    except Exception as e:
        logger.error(f"Failed executing run_apply_task: {e}")
        raise e
    finally:
        loop.close()
