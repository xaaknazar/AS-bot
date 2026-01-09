from fastapi import APIRouter

from app.service.tcp_modbus import TcpModbusSensorService
from app.schemas import sensor as schemas
from app.schemas.data import TitleValueSchema


router = APIRouter()
service = TcpModbusSensorService()


@router.get(
    "",
    response_model=list[schemas.TcpModbusSensorSchema],
    response_model_by_alias=False,
)
def get_sensors(
        name: str = None,
        ip_address: str = None,
        description: str = None,
        metric_unit: str = None,
        enabled: bool = None
):
    return service.get_all(
        name, ip_address, description, metric_unit, enabled
    )


@router.get(
    "/{id}",
    response_model=schemas.TcpModbusSensorSchema,
    response_model_by_alias=False,
)
def get_sensor_by_id(id: str):
    return service.get_by_id(id)


@router.post(
    "",
    status_code=201,
    response_model=schemas.TcpModbusSensorSchema,
    response_model_by_alias=False,
)
def create_sensor(dto: schemas.TcpModbusSensorCreate):
    return service.create(dto)


@router.patch(
    "/{id}",
    response_model=schemas.TcpModbusSensorSchema,
    response_model_by_alias=False,
)
def update_sensor(
        id: str,
        dto: schemas.TcpModbusSensorUpdate
):
    return service.update(id, dto)


@router.delete(
    "/{id}",
    status_code=204,
)
def delete_sensor(id: str):
    service.delete(id)


@router.post(
    "/check-value",
    response_model=TitleValueSchema,
)
def check_value(dto: schemas.TcpModbusSensorCreate):
    return service.get_value(dto)


@router.get(
    "/{id}/check-value",
    response_model=TitleValueSchema,
)
def check_value_by_id(id: str):
    data, _ = service.get_value_by_id(id)
    return data
