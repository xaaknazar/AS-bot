import logging
from bson import ObjectId
from fastapi import HTTPException

import snap7
import snap7.util as util

from app.schemas import sensor as schemas
from app.schemas.data import TitleValueSchema
from app.service.base import BaseSensorService


class Snap7Client:
    def __init__(self, ip: str, rack: int, slot: int):
        self.ip = ip
        self.rack = rack
        self.slot = slot
        self.client = snap7.client.Client()

    def connect(self):
        self.client.connect(self.ip, self.rack, self.slot)

    def disconnect(self):
        self.client.disconnect()
        self.client.destroy()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def read_db(self, db_number: int, start: int, size: int) -> float:
        if not self.client.get_connected():
            raise Exception("Not connected to PLC.")
        byte_array = self.client.db_read(db_number, start, size)
        logging.info(f"| PLC | Read value from: {self.ip}, rack={self.rack}")
        return util.get_real(byte_array, 0)


class PlcSensorService(BaseSensorService):
    def __init__(self):
        super().__init__("plc_sensors")

    @staticmethod
    def _read_sensor(
            dto: schemas.PlcSensorSchema | schemas.PlcSensorCreate
    ) -> float | None:
        try:
            with Snap7Client(str(dto.ip_address), dto.rack, dto.slot) as client:
                return client.read_db(dto.db, dto.offset, dto.size)
        except Exception:
            logging.error(
                "| PLC | Error reading value from:"
                f" ip={dto.ip_address}, db={dto.db},"
                f" start={dto.offset}, size={dto.size}"
            )
            return None

    def get_all(
            self,
            name: str | None,
            ip_address: str | None,
            description: str | None,
            metric_unit: str | None,
            enabled: bool | None,
    ) -> list[schemas.PlcSensorSchema]:
        result = self._get_all(
            name, ip_address, description, metric_unit, enabled
        )
        return [schemas.PlcSensorSchema(**item) for item in result]

    def get_by_id(self, id: str) -> schemas.PlcSensorSchema:
        sensor = self._get_by_id(id)
        return schemas.PlcSensorSchema(**sensor)

    def create(self, dto: schemas.PlcSensorCreate) -> schemas.PlcSensorSchema:
        sensor = self._create(dto)
        return schemas.PlcSensorSchema(**sensor)

    def update(self, id: str, dto: schemas.PlcSensorUpdate) -> schemas.PlcSensorSchema:
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
        return schemas.PlcSensorSchema(**sensor)

    def get_value(self, dto: schemas.PlcSensorCreate) -> TitleValueSchema:
        data, _ = self._read_by_dto(dto, True)
        return data

    def get_value_by_id(
            self, id: str, raise_exception: bool = True
    ) -> tuple[TitleValueSchema | None, bool]:
        sensor = self.get_by_id(id)
        return self._read_by_dto(sensor, True, raise_exception)
