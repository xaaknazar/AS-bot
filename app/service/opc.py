import logging

from bson import ObjectId
from fastapi import HTTPException
from opcua import Client, Node

from app.schemas import sensor as schemas
from app.schemas.data import TitleValueSchema
from app.service.base import BaseSensorService


class OpcClient:
    def __init__(self, ip_address: str, port: int):
        self.opc_url = f"opc.tcp://{ip_address}:{port}"
        self.client = None

    def connect(self):
        if self.client is None:
            self.client = Client(self.opc_url)
        self.client.connect()

    def disconnect(self):
        if self.client is not None:
            self.client.disconnect()
            self.client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def read_value(self, node_id: schemas.OpcNodeID) -> float:
        if self.client is None:
            raise Exception("Not connected to OPC server.")
        node = self.client.get_node(str(node_id))
        value = node.get_value()
        if value is None:
            raise Exception("No data available for the specified Node ID.")
        logging.info(f"| OPC | Read value from: {self.opc_url}, node_id='{node_id}'")
        return value

    def get_root(self):
        if self.client is None:
            raise Exception("Not connected to OPC server.")
        return self.client.get_root_node()

    def get_node_tree(
            self,
            node: Node,
            depth: int = 0,
            max_depth: int = 3
    ) -> schemas.OpcNodeSchema | None:
        if depth > max_depth:
            return None

        try:
            browse_name = node.get_browse_name().to_string()
            value = None

            try:
                raw_value = node.get_value()
                if isinstance(raw_value, (int, float)):
                    value = raw_value
            except:
                pass

            children = []
            for child in node.get_children():
                child_data = self.get_node_tree(child, depth + 1, max_depth)
                if child_data:
                    children.append(child_data)

            if value is None and not children:
                return None

            return schemas.OpcNodeSchema(
                browse_name=browse_name,
                node_id=schemas.OpcNodeID.from_node_id(node.nodeid),
                value=value,
                children=children
            )
        except Exception:
            raise


class OpcSensorService(BaseSensorService):
    def __init__(self):
        super().__init__("opc_sensors")

    @staticmethod
    def _read_sensor(
            dto: schemas.OpcSensorSchema | schemas.OpcSensorCreate
    ) -> float | None:
        try:
            with OpcClient(str(dto.ip_address), dto.port) as client:
                return client.read_value(dto.node_id)
        except Exception:
            logging.error(
                "| OPC | Error reading value from:"
                f" ip={dto.ip_address},"
                f" node_id='{dto.node_id}'"
            )
            return None

    @staticmethod
    def get_node_tree(
            ip: str, port: int, max_depth: int
    ) -> schemas.OpcNodeSchema:
        try:
            with OpcClient(ip, port) as client:
                root = client.get_root()
                return client.get_node_tree(
                    node=root, max_depth=max_depth
                )
        except Exception:
            logging.error(
                "| OPC | Error reading node tree from:"
                f" ip={ip}, port={port}"
            )
            raise HTTPException(400, "Error reading node tree")

    def get_all(
            self,
            name: str | None,
            ip_address: str | None,
            description: str | None,
            metric_unit: str | None,
            enabled: bool | None,
    ) -> list[schemas.OpcSensorSchema]:
        result = self._get_all(
            name, ip_address, description, metric_unit, enabled
        )
        return [schemas.OpcSensorSchema(**item) for item in result]

    def get_by_id(self, id: str) -> schemas.OpcSensorSchema:
        sensor = self._get_by_id(id)
        return schemas.OpcSensorSchema(**sensor)

    def create(self, dto: schemas.OpcSensorCreate) -> schemas.OpcSensorSchema:
        sensor = self._create(dto)
        return schemas.OpcSensorSchema(**sensor)

    def update(self, id: str, dto: schemas.OpcSensorUpdate) -> schemas.OpcSensorSchema:
        sensor = self.get_by_id(id)
        values = dto.model_dump(exclude_unset=True)
        if not values:
            raise HTTPException(400, "No values to update")

        if values.get("node_id"):
            values["node_id"] = schemas.OpcNodeID(**values["node_id"])

        sensor.__dict__.update(values)
        sensor.enabled = True
        self._read_by_dto(sensor)

        if values.get("node_id"):
            values["node_id"] = values["node_id"].model_dump()

        sensor = self.repo.update_document(
            ObjectId(id), values, True, self.collection_name
        )
        return schemas.OpcSensorSchema(**sensor)

    def get_value(self, dto: schemas.OpcSensorCreate) -> TitleValueSchema:
        data, _ = self._read_by_dto(dto, True)
        return data

    def get_value_by_id(
            self, id: str, raise_exception: bool = True
    ) -> tuple[TitleValueSchema | None, bool]:
        sensor = self.get_by_id(id)
        return self._read_by_dto(sensor, True, raise_exception)
