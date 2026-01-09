import pytz

from fastapi import HTTPException
from pymongo import MongoClient

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from app.service.base import SingletonMeta
from app.schemas.jobs import JobSchema
from app.config import settings
from app.service import data


class SchedulerService(metaclass=SingletonMeta):
    def __init__(self):
        self.job_store = MongoDBJobStore(
            client=MongoClient(settings.mongodb_url)
        )
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.scheduler = BackgroundScheduler(
            jobstores={'default': self.job_store},
            executors={'default': self.executor},
            job_defaults={'coalesce': True, 'max_instances': 2},
            timezone=pytz.timezone(settings.timezone)
        )

    def start(self):
        self.scheduler.start()

    def stop(self):
        self.scheduler.shutdown()

    def pause(self):
        self.scheduler.pause()

    def resume(self):
        self.scheduler.resume()

    def pause_job(self, name: str) -> None:
        self.get_job(name)
        self.scheduler.pause_job(name)

    def resume_job(self, name: str) -> None:
        self.get_job(name)
        self.scheduler.resume_job(name)

    def remove_job(self, name: str) -> None:
        self.get_job(name)
        self.scheduler.remove_job(name)

    def get_jobs(self) -> list[JobSchema]:
        jobs = self.scheduler.get_jobs()
        return [JobSchema.from_apscheduler(job) for job in jobs]

    def get_job(self, name: str) -> JobSchema:
        job = self.scheduler.get_job(name)
        if job is None:
            raise HTTPException(404, "Job not found")
        return JobSchema.from_apscheduler(job)

    def job_exists(self, name: str) -> bool:
        return self.scheduler.get_job(name) is not None

    def send_report(self, name: str) -> None:
        job = self.get_job(name)
        if not job.shift_report:
            raise HTTPException(
                400,
                "Job is not configured to send shift reports"
            )

        if not data.send_report(job.name, job.description, job.diff_field):
            raise HTTPException(
                500,
                "Failed to send shift report"
            )

    def add_job(
            self,
            name: str,
            func: any,
            trigger: str,
            args: dict,
            week: int | str | None = None,
            day_of_week: int | str | None = None,
            day: int | str | None = None,
            hour: int | str | None = None,
            minute: int | str | None = None,
            second: int | str | None = None,
            interval_metric: str | None = None,
            interval: int | None = None
    ) -> JobSchema:
        trigger_args = {interval_metric: interval} if interval_metric else {}

        if week is not None:
            trigger_args['week'] = week
        if day_of_week is not None:
            trigger_args['day_of_week'] = day_of_week
        if day is not None:
            trigger_args['day'] = day
        if hour is not None:
            trigger_args['hour'] = hour
        if minute is not None:
            trigger_args['minute'] = minute
        if second is not None:
            trigger_args['second'] = second

        job = self.scheduler.add_job(
            func, id=name, name=name, trigger=trigger,
            kwargs=args, misfire_grace_time=3600,
            **trigger_args
        )

        return JobSchema.from_apscheduler(job, True)
