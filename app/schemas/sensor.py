from typing import Literal
from datetime import datetime
from typing_extensions import Annotated

from pydantic import (
    BaseModel, ConfigDict, Field, constr, IPvAnyAddress, conint, field_serializer
)
from pydantic.functional_validators import BeforeValidator
from opcua.ua import NodeId


PyObjectId = Annotated[str, BeforeValidator(str)]
ModbusDataType = Literal[
    "INT16", "UINT16",
    "INT32", "UINT32",
    "INT64", "UINT64",
    "FLOAT32", "FLOAT64",
    # "STRING", "BITS"
]
WordOrder = Literal["big", "little"]
Port = conint(ge=1, le=65535)


class BaseSensorCreateModel(BaseModel):
    ip_address: IPvAnyAddress

    @field_serializer("ip_address")
    def serialize_ip(self, ip: IPvAnyAddress) -> str:
        return str(ip) if ip else None


class OpcNodeID(BaseModel):
    namespace: int
    identifier: int | str
    variable: str | None = None

    def __str__(self):
        if isinstance(self.identifier, int):
            return f'ns={self.namespace};i={self.identifier}'
        if isinstance(self.identifier, str) and self.variable:
            return f'ns={self.namespace};s="{self.identifier}"."{self.variable}"'
        elif isinstance(self.identifier, str):
            return f'ns={self.namespace};s={self.identifier}'

    @classmethod
    def from_node_id(cls, node_id: NodeId):
        return cls(
            namespace=node_id.NamespaceIndex,
            identifier=node_id.Identifier
        )


class OpcSensorCreate(BaseSensorCreateModel):
    name: constr(min_length=3, max_length=30)
    title: constr(min_length=3, max_length=30)
    description: constr(min_length=3, max_length=100)
    port: Port
    node_id: OpcNodeID
    enabled: bool = True
    metric_unit: constr(min_length=3, max_length=30)
    coefficient: float


class OpcSensorUpdate(BaseSensorCreateModel):
    name: constr(min_length=3, max_length=30) = None
    title: constr(min_length=3, max_length=30) = None
    description: constr(min_length=3, max_length=100) = None
    ip_address: IPvAnyAddress = None
    port: Port = None
    node_id: OpcNodeID = None
    enabled: bool = None
    metric_unit: constr(min_length=3, max_length=30) = None
    coefficient: float = None


class OpcNodeSchema(BaseModel):
    browse_name: str
    node_id: OpcNodeID
    value: float
    children: list["OpcNodeSchema"] | None = None

    model_config = ConfigDict(from_attributes=True)


class OpcSensorSchema(BaseModel):
    id: PyObjectId = Field(alias='_id', default=None)
    name: str
    title: str
    description: str
    ip_address: str
    port: int
    node_id: OpcNodeID
    enabled: bool
    metric_unit: str
    coefficient: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlcSensorCreate(BaseSensorCreateModel):
    name: constr(min_length=3, max_length=30)
    title: constr(min_length=3, max_length=30)
    description: constr(min_length=3, max_length=100)
    db: int
    rack: int
    slot: int
    offset: int
    size: int
    enabled: bool = True
    metric_unit: constr(min_length=3, max_length=30)
    coefficient: float


class PlcSensorUpdate(BaseSensorCreateModel):
    name: constr(min_length=3, max_length=30) = None
    title: constr(min_length=3, max_length=30) = None
    description: constr(min_length=3, max_length=100) = None
    ip_address: IPvAnyAddress = None
    db: int = None
    rack: int = None
    slot: int = None
    offset: int = None
    size: int = None
    enabled: bool = None
    metric_unit: constr(min_length=3, max_length=30) = None
    coefficient: float = None


class PlcSensorSchema(BaseModel):
    id: PyObjectId = Field(alias='_id', default=None)
    name: str
    title: str
    description: str
    ip_address: str
    db: int
    rack: int
    slot: int
    offset: int
    size: int
    enabled: bool
    metric_unit: str
    coefficient: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TcpModbusSensorCreate(BaseSensorCreateModel):
    name: constr(min_length=3, max_length=30)
    title: constr(min_length=3, max_length=30)
    description: constr(min_length=3, max_length=100)
    port: Port
    reg_address: int
    reg_number: int
    unit_id: int = 1
    dtype: ModbusDataType
    word_order: WordOrder = "big"
    enabled: bool = True
    metric_unit: constr(min_length=3, max_length=30)
    coefficient: float


class TcpModbusSensorUpdate(BaseSensorCreateModel):
    name: constr(min_length=3, max_length=30) = None
    title: constr(min_length=3, max_length=30) = None
    description: constr(min_length=3, max_length=100) = None
    ip_address: IPvAnyAddress = None
    port: Port = None
    reg_address: int = None
    reg_number: int = None
    unit_id: int = None
    dtype: ModbusDataType = None
    word_order: WordOrder = None
    enabled: bool = None
    metric_unit: constr(min_length=3, max_length=30) = None
    coefficient: float = None


class TcpModbusSensorSchema(BaseModel):
    id: PyObjectId = Field(alias='_id', default=None)
    name: str
    title: str
    description: str
    ip_address: str
    port: int
    reg_address: int
    reg_number: int
    unit_id: int
    dtype: str
    word_order: WordOrder
    enabled: bool
    metric_unit: str
    coefficient: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Sensor(BaseModel):
    id: str
    type: Literal["opc", "plc", "tcp_modbus"]
