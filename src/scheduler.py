from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler

executors = {"default": ThreadPoolExecutor(1)}

scheduler = BackgroundScheduler(executors=executors)


def add_task(func, trigger, **trigger_args):
    scheduler.add_job(func, trigger, coalesce=True, max_instances=1, **trigger_args)


def start_scheduler():
    if not scheduler.running:
        scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
