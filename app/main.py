from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.config import setup_middleware
from app.routes.main import setup_routers
from app.service.scheduler import SchedulerService
from app.service.sensor import SensorClientService


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_service = SchedulerService()
    sensor_service = SensorClientService()
    sensor_service.create_indexes()
    scheduler_service.start()
    yield
    scheduler_service.stop()


def init_app() -> FastAPI:
    app = FastAPI(
        title="SCHEDULER-SYNC-PRO",
        lifespan=lifespan,
        docs_url="/scheduler-sync-pro/docs",
        openapi_url="/scheduler-sync-pro/openapi.json",
    )
    setup_routers(app)
    setup_middleware(app)

    return app
