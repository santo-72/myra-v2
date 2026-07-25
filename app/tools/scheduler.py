from apscheduler.schedulers.asyncio import AsyncIOScheduler
import structlog
from typing import Callable

logger = structlog.get_logger(__name__)

class TaskScheduler:
    """Manages scheduled background tasks for M.Y.R.A"""
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        logger.info("TaskScheduler initialized")

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("TaskScheduler started")

    def add_task(self, func: Callable, trigger: str, **kwargs) -> str:
        """
        Add a task to the scheduler.
        trigger: 'date', 'interval', or 'cron'
        """
        try:
            job = self.scheduler.add_job(func, trigger=trigger, **kwargs)
            logger.info(f"Task scheduled: {job.id}")
            return job.id
        except Exception as e:
            logger.error("Failed to schedule task", error=str(e))
            return ""

    def remove_task(self, job_id: str):
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Task removed: {job_id}")
        except Exception as e:
            logger.error(f"Failed to remove task {job_id}", error=str(e))

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("TaskScheduler shut down")
