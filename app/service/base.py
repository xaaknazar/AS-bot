from bson import ObjectId
from fastapi import HTTPException

from app.database.mongodb import MongoDBRepository
from app.schemas.data import TitleValueSchema
from app.config import settings


class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class BaseSensorService(metaclass=SingletonMeta):
    def __init__(self, collection_name: str):
        self.repo = MongoDBRepository(settings.mongodb_sensors_db)
        self.collection_name = collection_name

    @staticmethod
    def _check_coefficient(coefficient: float) -> float:
        if coefficient <= 0.0:
            return 1
        else:
            return coefficient

    def _get_all(
            self,
            name: str | None,
            ip_address: str | None,
            description: str | None,
            metric_unit: str | None,
            enabled: bool | None,
    ) -> list[dict]:
        query = {}
        if name:
            query["name"] = {"$regex": name}
        if ip_address:
            query["ip_address"] = {"$regex": ip_address}
        if description:
            query["description"] = {"$regex": description}
        if metric_unit:
            query["metric_unit"] = {"$regex": metric_unit}
        if enabled is not None:
            query["enabled"] = enabled

        return self.repo.get_collection(
            self.collection_name, query=query
        )

    def _get_by_id(self, id: str) -> dict:
        sensor = self.repo.get_document(ObjectId(id), self.collection_name)
        if sensor is None:
            raise HTTPException(404, "Sensor not found")
        return sensor

    def _create(self, dto) -> dict:
        dto.enabled = True
        self._read_by_dto(dto)
        return self.repo.create_document(
            dto.model_dump(), True, self.collection_name
        )

    def create_index(self):
        self.repo.create_index(self.collection_name, "name")

    def delete(self, id: str):
        self.repo.delete_document(ObjectId(id), self.collection_name)

    @staticmethod
    def _read_sensor(dto) -> int | float | None:
        raise NotImplementedError("Subclasses must implement `_read_sensor`")

    def _read_by_dto(
            self,
            dto,
            return_as_schema: bool = False,
            raise_exception: bool = True,
    ) -> tuple[int | float | TitleValueSchema | None, bool]:
        if not dto.enabled:
            if raise_exception:
                raise HTTPException(
                    403, f"Sensor {dto.name} is disabled"
                )
            return None, False

        coefficient = self._check_coefficient(dto.coefficient)
        value = self._read_sensor(dto)

        if value is None:
            if raise_exception:
                raise HTTPException(
                    404, f"Value not found for sensor {dto.name}"
                )
            # 2nd value indicates fault
            return None, True

        weighted_value = coefficient * value

        if return_as_schema:
            return TitleValueSchema(
                title=dto.title, value=weighted_value, metric_unit=dto.metric_unit
            ), False

        return weighted_value, False
