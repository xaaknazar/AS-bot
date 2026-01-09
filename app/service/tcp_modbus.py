import logging
from bson import ObjectId
from fastapi import HTTPException
from pymodbus.client import ModbusTcpClient

from app.schemas import sensor as schemas
from app.schemas.data import TitleValueSchema
from app.service.base import BaseSensorService


class TcpModbusSensorService(BaseSensorService):
    def __init__(self):
        super().__init__("tcp_modbus_sensors")

    @staticmethod
    def _read_sensor(
            dto: schemas.TcpModbusSensorSchema | schemas.TcpModbusSensorCreate,
    ) -> float | int | None:
        try:
            client = ModbusTcpClient(host=str(dto.ip_address), port=dto.port)
            with client:
                response = client.read_holding_registers(
                    address=dto.reg_address, count=dto.reg_number, device_id=dto.unit_id
                )
                data_type = client.DATATYPE[dto.dtype]
                value = client.convert_from_registers(
                    registers=response.registers,
                    data_type=data_type, # type: ignore
                    word_order=dto.word_order
                )
            logging.info(
                f"| TCP | Read value from:"
                f" ip={dto.ip_address},"
                f" port={dto.port}"
            )
            return sum(value) if isinstance(value, list) else value
        except Exception:
            logging.error(
                "| TCP | Error reading value from:"
                f" ip={dto.ip_address},"
                f" port={dto.port},"
                f" reg_address={dto.reg_address}, reg_number={dto.reg_number},"
                f" unit_id={dto.unit_id}, dtype={dto.dtype}"
            )
            return None

    def get_all(
            self,
            name: str | None,
            ip_address: str | None,
            description: str | None,
            metric_unit: str | None,
            enabled: bool | None,
    ) -> list[schemas.TcpModbusSensorSchema]:
        result = self._get_all(
            name, ip_address, description, metric_unit, enabled
        )
        return [schemas.TcpModbusSensorSchema(**item) for item in result]

    def get_by_id(self, id: str) -> schemas.TcpModbusSensorSchema:
        sensor = self._get_by_id(id)
        return schemas.TcpModbusSensorSchema(**sensor)

    def create(self, dto: schemas.TcpModbusSensorCreate) -> schemas.TcpModbusSensorSchema:
        sensor = self._create(dto)
        return schemas.TcpModbusSensorSchema(**sensor)

    def update(self, id: str, dto: schemas.TcpModbusSensorUpdate) -> schemas.TcpModbusSensorSchema:
        sensor = self.get_by_id(id)
        values = dto.model_dump(exclude_unset=True)
        if not values:
            raise HTTPException(400, "No values to update")

        sensor.__dict__.update(values)
        sensor.enabled = True
        self._read_by_dto(sensor)

        sensor = self.repo.update_document(
            ObjectId(id), values, True, self.collection_name
        )
        return schemas.TcpModbusSensorSchema(**sensor)

    def get_value(self, dto: schemas.TcpModbusSensorCreate) -> TitleValueSchema:
        data, _ = self._read_by_dto(dto, True)
        return data

    def get_value_by_id(
            self, id: str, raise_exception: bool = True
    ) -> tuple[TitleValueSchema | None, bool]:
        sensor = self.get_by_id(id)
        return self._read_by_dto(sensor, True, raise_exception)
