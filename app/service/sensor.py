from app.service.base import SingletonMeta
from app.service.opc import OpcSensorService
from app.service.plc import PlcSensorService
from app.service.tcp_modbus import TcpModbusSensorService
from app.schemas.data import TitleValueSchema
from app.schemas.sensor import Sensor


class SensorClientService(metaclass=SingletonMeta):
    def __init__(self):
        self.opc_service = OpcSensorService()
        self.plc_service = PlcSensorService()
        self.tcp_service = TcpModbusSensorService()

    def create_indexes(self):
        self.opc_service.create_index()
        self.plc_service.create_index()
        self.tcp_service.create_index()

    def read_sensor(self, sensor: Sensor) -> tuple[TitleValueSchema | None, bool]:
        data, is_fault = None, False
        match sensor.type:
            case "opc":
                data, is_fault = self.opc_service.get_value_by_id(
                    sensor.id, False
                )
            case "plc":
                data, is_fault = self.plc_service.get_value_by_id(
                    sensor.id, False
                )
            case "tcp_modbus":
                data, is_fault = self.tcp_service.get_value_by_id(
                    sensor.id, False
                )

        return data, is_fault

    def validate_sensor_args(
            self,
            opc_sensors_id: list[str] | None,
            plc_sensors_id: list[str] | None,
            tcp_modbus_sensors_id: list[str] | None
    ) -> list[dict]:
        sensors = []
        if opc_sensors_id:
            for id in opc_sensors_id:
                self.opc_service.get_value_by_id(id)
                sensors.append({"id": id, "type": "opc"})
        if plc_sensors_id:
            for id in plc_sensors_id:
                self.plc_service.get_value_by_id(id)
                sensors.append({"id": id, "type": "plc"})
        if tcp_modbus_sensors_id:
            for id in tcp_modbus_sensors_id:
                self.tcp_service.get_value_by_id(id)
                sensors.append({"id": id, "type": "tcp_modbus"})

        return sensors

    def read_sensors_by_id(
            self, sensors: list[Sensor], summation: bool
    ) -> tuple[list[TitleValueSchema], bool, bool]:
        values = []
        title, metric_unit, is_zero, has_fault = "Unknown", "~", True, False
        for sensor in sensors:
            data, sensor_fault = self.read_sensor(sensor)

            if sensor_fault:
                has_fault = True

            if data is None:
                continue

            if data.value > 0:
                is_zero = False

            if summation:
                values.append(data.value)
                title, metric_unit = data.title, data.metric_unit
            else:
                values.append(data)

        if not values:
            return (
                [TitleValueSchema(title=title, value=0.0, metric_unit=metric_unit)],
                is_zero,
                has_fault
            )
        if summation:
            return (
                [TitleValueSchema(title=title, value=sum(values), metric_unit=metric_unit)],
                is_zero,
                has_fault
            )

        return values, is_zero, has_fault
