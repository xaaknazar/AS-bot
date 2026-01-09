from fastapi import APIRouter
from pydantic import IPvAnyAddress, conint

from app.service.opc import OpcSensorService
from app.schemas import sensor as schemas
from app.schemas.data import TitleValueSchema


router = APIRouter()
service = OpcSensorService()


@router.get(
    "",
    response_model=list[schemas.OpcSensorSchema],
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
    response_model=schemas.OpcSensorSchema,
    response_model_by_alias=False,
)
def get_sensor_by_id(id: str):
    return service.get_by_id(id)


@router.get(
    "/node/tree",
    response_model=schemas.OpcNodeSchema,
)
def get_node_tree(
        ip_address: IPvAnyAddress,
        port: conint(ge=1, le=65535),
        max_depth: int = 3
):
    return service.get_node_tree(
        str(ip_address), port, max_depth
    )


@router.post(
    "",
    status_code=201,
    response_model=schemas.OpcSensorSchema,
    response_model_by_alias=False,
)
def create_sensor(dto: schemas.OpcSensorCreate):
    return service.create(dto)


@router.patch(
    "/{id}",
    response_model=schemas.OpcSensorSchema,
    response_model_by_alias=False,
)
def update_sensor(
        id: str,
        dto: schemas.OpcSensorUpdate
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
def check_value(dto: schemas.OpcSensorCreate):
    return service.get_value(dto)


@router.get(
    "/{id}/check-value",
    response_model=TitleValueSchema,
)
def check_value_by_id(id: str):
    data, _ = service.get_value_by_id(id)
    return data
