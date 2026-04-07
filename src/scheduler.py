from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from .constants import DB_URL
from .logging_config import get_logger

logger = get_logger(__name__)
jobstores = {
    "default": SQLAlchemyJobStore(
        url=DB_URL, engine_options={"connect_args": {"timeout": 2}}
    )
}
executors = {
    "bottles": ThreadPoolExecutor(1),
    "training": ThreadPoolExecutor(1),
    "fight": ThreadPoolExecutor(1),
    "monitor": ThreadPoolExecutor(1),
}
scheduler = BackgroundScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults={"misfire_grace_time": 30, "coalesce": True},
)


def _job_executed(event):
    if event.exception:
        logger.error(f"Job {event.job_id} failed: {event.exception}")
    else:
        logger.debug(f"Job {event.job_id} executed successfully")


scheduler.add_listener(_job_executed, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)


def add_task(func, trigger, job_id=None, **trigger_args):
    scheduler.add_job(
        func,
        trigger,
        id=job_id,
        coalesce=True,
        max_instances=1,
        replace_existing=True,
        **trigger_args,
    )


def start_scheduler():
    if not scheduler.running:
        try:
            jobstores["default"].remove_all_jobs()
        except Exception as e:
            logger.debug(f"Could not clear jobstore: {e}")
        scheduler.start()
        try:
            for job in scheduler.get_jobs():
                try:
                    job.remove()
                except Exception:
                    pass
        except Exception:
            pass


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
