from fastapi import HTTPException

from app import utils
from app.service import data
from app.service.scheduler import SchedulerService
from app.service.sensor import SensorClientService
from app.database import MongoDBRepository

from app.schemas.jobs import (
    JobCreate, CronTask, PeriodicTask, JobSchema
)
from app.config import settings


repo = MongoDBRepository(settings.mongodb_db)
scheduler_service = SchedulerService()
sensor_service = SensorClientService()


def add_cron_job(
        job_name: str, func: callable, details: CronTask, args: dict
) -> JobSchema:
    return scheduler_service.add_job(
        name=job_name, func=func, trigger="cron", args=args,
        week=details.week, day_of_week=details.day_of_week,
        day=details.day, hour=details.hour,
        minute=details.minute, second=details.second,
    )


def add_periodic_job(
        job_name: str, func: callable, details: PeriodicTask, args: dict
) -> JobSchema:
    return scheduler_service.add_job(
        name=job_name, func=func,  trigger="interval",
        args=args, interval_metric=details.metric,
        interval=details.interval,
    )


def validate_job_args(
        func: callable,
        collection_name: str,
        job_description: str,
        sensors: list[dict],
        tg_send: bool,
        shift_report: bool,
        summation: bool,
        speed_info: bool,
        chat: str | None
):
    if func == data.process_cumulative_data:
        return {
            "collection_name": collection_name,
            "job_description": job_description,
            "sensors": sensors,
            "tg_send": tg_send,
            "shift_report": shift_report,
            "speed_info": speed_info,
            "chat": chat
        }
    if func == data.process_data:
        return {
            "collection_name": collection_name,
            "job_description": job_description,
            "sensors": sensors,
            "tg_send": tg_send,
            "shift_report": shift_report,
            "summation": summation,
            "chat": chat
        }
    return None


def create_report_job(dto: JobCreate, sensors: list[dict]) -> list[JobSchema]:
    dto.name = dto.name + "_shift_report"
    if dto.diff_field:
        func = data.process_cumulative_data
        repo.create_collection(dto.name)
    else:
        func = data.process_data

    jobs = []
    shifts, shift_hours = ["am", "pm"], utils.get_shift_times()
    for i in range(len(shifts)):
        job_name = f"{dto.name}_{shifts[i]}"
        details = CronTask(
            hour=shift_hours[i][0],
            minute=shift_hours[i][1],
            second=30
        )
        args = validate_job_args(
            func, dto.name, dto.description,
            sensors, dto.tg_send, dto.shift_report,
            dto.summation, dto.speed_info, dto.chat
        )
        jobs.append(add_cron_job(job_name, func, details, args))

    return jobs


def create_job(dto: JobCreate) -> list[JobSchema]:
    if scheduler_service.job_exists(dto.name):
        raise HTTPException(
            409, "Job with this name already exists"
        )
    if (dto.multiple_sensors and dto.diff_field) and not dto.summation:
        raise HTTPException(
            400,
            "If diff_field is True,"
            " summation must be True when there are multiple sensors."
        )
    if dto.shift_report and not dto.tg_send:
        raise HTTPException(
            400,
            "Telegram notifications must be enabled for shift reports."
        )

    sensors = sensor_service.validate_sensor_args(
        dto.opc_sensors_id, dto.plc_sensors_id, dto.tcp_modbus_sensors_id
    )
    repo.create_collection(dto.name)

    if dto.diff_field:
        func = data.process_cumulative_data
    else:
        func = data.process_data

    args = validate_job_args(
        func, dto.name, dto.description,
        sensors, dto.tg_send, False,
        dto.summation, dto.speed_info, dto.chat
    )

    result, jobs = [], []
    if dto.details.trigger == "interval":
        job = add_periodic_job(dto.name, func, dto.details.periodic_task, args)
    else: # dto.trigger == "cron"
        job = add_cron_job(dto.name, func, dto.details.cron_task, args)
    if dto.shift_report:
        jobs = create_report_job(dto, sensors)

    result.append(job)
    result.extend(jobs)

    return result


def delete_job(name: str, remove_collection: bool = False, delete_all: bool = False):
    job = scheduler_service.get_job(name)
    if not job:
        raise HTTPException(404, "Job not found")

    name = job.name
    if name.endswith("_shift_report_am"):
        scheduler_service.remove_job(name)
        return
    elif name.endswith("_shift_report_pm"):
        scheduler_service.remove_job(name)
        return
    else:
        scheduler_service.remove_job(name)

    if remove_collection:
        repo.delete_collection(name)

    if delete_all:
        shift_report = False
        for suffix in ["_shift_report_am", "_shift_report_pm"]:
            shift_job_name = name + suffix
            if scheduler_service.job_exists(shift_job_name):
                shift_report = True
                scheduler_service.remove_job(shift_job_name)
        if shift_report:
            repo.delete_collection(name + "_shift_report")
