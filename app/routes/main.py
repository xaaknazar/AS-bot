from fastapi import FastAPI

from .opc import router as router_opc
from .plc import router as router_plc
from .tcp_modbus import router as router_tcp_modbus
from .jobs import router as router_jobs
from app.service.websocket import router as router_ws


def setup_routers(app: FastAPI) -> None:
    app.include_router(router_opc, prefix="/api/opc", tags=["Opc Sensors"])
    app.include_router(router_plc, prefix="/api/plc", tags=["Plc Sensors"])
    app.include_router(router_tcp_modbus, prefix="/api/tcp-modbus", tags=["Tcp Modbus Sensors"])
    app.include_router(router_jobs, prefix="/api/jobs", tags=["Jobs"])
    app.include_router(router_ws, prefix="/api", tags=["Websocket"])
