from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from .constants import DB_URL

# Configure job store for persistence
jobstores = {
    'default': SQLAlchemyJobStore(url=DB_URL)
}

executors = {"default": ThreadPoolExecutor(1)}

scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors)


def add_task(func, trigger, job_id=None, **trigger_args):
    scheduler.add_job(
        func,
        trigger,
        id=job_id,
        coalesce=True,
        max_instances=1,
        replace_existing=True,
        **trigger_args
    )


def start_scheduler():
    if not scheduler.running:
        scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
