from datetime import datetime as datetime_
from pydantic import BaseModel, Field

from app.utils import current_datetime


class DataSchema(BaseModel):
    datetime: datetime_ = Field(default_factory=current_datetime)
    value: float
    metric_unit: str


class DataSchemaExt(DataSchema):
    difference: float
    speed: float


class TitleValueSchema(BaseModel):
    title: str
    value: float
    metric_unit: str


class MultipleDataSchema(BaseModel):
    datetime: datetime_ = Field(default_factory=current_datetime)
    values: list[TitleValueSchema]


class RvoWsDataSchema(BaseModel):
    shift_id: int
    shift_name: str
    speed: float
    speed_for_shift: float
    produced: float
