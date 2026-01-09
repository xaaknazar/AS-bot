from typing import Literal
from datetime import datetime
from pydantic import (
    BaseModel, constr, model_validator, conint, computed_field
)
from apscheduler.job import Job
from apscheduler.triggers.interval import IntervalTrigger


Trigger = Literal["interval", "cron"]
Metric = Literal["seconds", "minutes", "hours", "days", "weeks"]
Chat = Literal["production", "monitoring", "technology", "core_shop", "rvo"]
Name = constr(
    min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+_[a-zA-Z0-9_]+_[a-zA-Z0-9_]+$"
)


class PeriodicTask(BaseModel):
    metric: Metric
    interval: int


class CronTask(BaseModel):
    day: conint(ge=1, le=31) | str | None = "*"
    week: conint(ge=1, le=53) | str | None = "*"
    day_of_week: conint(ge=0, le=6) | str | None = "*"
    hour: conint(ge=0, le=23) | str | None = "*"
    minute: conint(ge=0, le=59) | str | None = "*"
    second: conint(ge=0, le=59) | str | None = "*"

    @classmethod
    def validate(cls, **kwargs):
        if not kwargs:
            raise ValueError(
                "At least one of the following parameters must be not null: "
                "day, week, day_of_week, hour, minute, second"
            )
        return kwargs


class JobDetails(BaseModel):
    trigger: Trigger
    periodic_task: PeriodicTask | None = None
    cron_task: CronTask | None = None

    @model_validator(mode='after')
    def validate_fields(self):
        if self.trigger == "interval" and self.periodic_task is None:
            raise ValueError("periodic_task must be not null")
        elif self.trigger == "cron" and self.cron_task is None:
            raise ValueError("cron_task must be not null")

        if self.periodic_task is None and self.cron_task is None:
            raise ValueError(
                "At least one of the following parameters must be not null: "
                "periodic_task, cron_task"
            )
        elif self.periodic_task is not None and self.cron_task is not None:
            raise ValueError(
                "Only one of the following parameters must be set: "
                "periodic_task, cron_task"
            )
        return self

    @classmethod
    def from_apscheduler(cls, trigger):
        if isinstance(trigger, IntervalTrigger):
            periodic = PeriodicTask(
                metric="minutes",
                interval=trigger.interval.total_seconds() // 60
            )
            return JobDetails(
                trigger="interval",
                periodic_task=periodic
            )
        else: # isinstance(trigger, CronTrigger)
            args = {
                f.name: int(str(f)) if str(f).isdigit() else str(f)
                for f in trigger.fields
            }
            return JobDetails(
                trigger="cron",
                cron_task=CronTask(**args)
            )


class JobCreate(BaseModel):
    name: Name
    description: constr(min_length=3, max_length=100)
    details: JobDetails
    opc_sensors_id: list[str] | None = None
    plc_sensors_id: list[str] | None = None
    tcp_modbus_sensors_id:  list[str] | None = None
    chat: Chat | None = None
    diff_field: bool | None = False
    tg_send: bool | None = True
    summation: bool | None = False
    speed_info: bool | None = False
    shift_report: bool | None = False

    @computed_field
    def multiple_sensors(self) -> bool:
        return sum([
                len(self.opc_sensors_id or []),
                len(self.plc_sensors_id or []),
                len(self.tcp_modbus_sensors_id or []),
        ]) > 1

    @model_validator(mode="after")
    def check_fields(self):
        ids = [self.opc_sensors_id, self.plc_sensors_id, self.tcp_modbus_sensors_id]
        if all(x in [None, []] for x in ids):
            raise ValueError(
                "At least one of opc_sensors_id, plc_sensors_id, "
                "or tcp_modbus_sensors_id must be set."
            )

        return self


class JobSchema(BaseModel):
    name: str
    description: str
    details: JobDetails
    opc_sensors_id: list[str] | None
    plc_sensors_id: list[str] | None
    tcp_modbus_sensors_id: list[str] | None
    chat: str | None
    diff_field: bool
    tg_send: bool
    summation: bool
    speed_info: bool
    shift_report: bool

    next_run_time: datetime | None

    @classmethod
    def from_apscheduler(cls, job: Job, exclude: bool = False):
        details = JobDetails.from_apscheduler(job.trigger)
        args = job.kwargs
        sensors = args.get("sensors", [])
        diff_field = False if job.func.__name__ == "process_data" else True
        summation = True if (len(sensors) > 1 and diff_field) else False
        opc_sensors_id = [s["id"] for s in sensors if s["type"] == "opc"] or None
        plc_sensors_id = [s["id"] for s in sensors if s["type"] == "plc"] or None
        tcp_modbus_sensors_id = [s["id"] for s in sensors if s["type"] == "tcp_modbus"] or None

        return cls(
            name=job.name,
            description=args.get("job_description"),
            details=details,
            opc_sensors_id=opc_sensors_id,
            plc_sensors_id=plc_sensors_id,
            tcp_modbus_sensors_id=tcp_modbus_sensors_id,
            chat=args.get("chat"),
            diff_field=diff_field,
            tg_send=args.get("tg_send"),
            summation=args.get("summation", summation),
            speed_info=args.get("speed_info", False),
            shift_report=args.get("shift_report"),
            next_run_time=job.next_run_time if not exclude else None
        )
