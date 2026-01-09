from fastapi import APIRouter

from app.service.scheduler import SchedulerService
from app.service import jobs as service
from app.schemas import jobs as schemas


router = APIRouter()
scheduler_service = SchedulerService()


@router.get(
    "",
    response_model=list[schemas.JobSchema],
)
def get_jobs():
    return scheduler_service.get_jobs()


@router.get(
    "/{name}",
    response_model=schemas.JobSchema,
)
def get_job_by_id(name: str):
    return scheduler_service.get_job(name)


@router.post(
    "",
    status_code=201,
    response_model=list[schemas.JobSchema],
)
def create_job(dto: schemas.JobCreate):
    return service.create_job(dto)


@router.delete(
    "/{name}",
    status_code=204,
)
def delete_job(
        name: str,
        remove_collection: bool = False,
        delete_all: bool = False
):
    return service.delete_job(name, remove_collection, delete_all)


@router.post(
    "/{name}/send-report",
    status_code=201,
    response_model=dict,
)
def send_report(name: str):
    scheduler_service.send_report(name)
    return {"message": f"Report job for ({name}) created successfully"}


@router.get(
    "/{name}/pause",
    response_model=dict,
)
def pause_job(name: str):
    scheduler_service.pause_job(name)
    return {"message": "Job successfully paused"}


@router.get(
    "/{name}/resume",
    response_model=dict,
)
def resume_job(name: str):
    scheduler_service.resume_job(name)
    return {"message": "Job successfully resumed"}


@router.get(
    "/pause/scheduler/",
    response_model=dict,
)
def pause_scheduler():
    scheduler_service.pause()
    return {"message": "Scheduler successfully paused"}


@router.get(
    "/resume/scheduler/",
    response_model=dict,
)
def resume_scheduler():
    scheduler_service.resume()
    return {"message": "Scheduler successfully resumed"}