import re
from datetime import datetime, timedelta
from operator import itemgetter

from app import utils
from app.service import idle
from app.service.sensor import SensorClientService
from app.service.telegram import TelegramBotService
from app.service.websocket import send_rvo_data
from app.database import MongoDBRepository

from app.schemas.sensor import Sensor
from app.schemas import data as schemas
from app.config import settings


repo = MongoDBRepository(settings.mongodb_db)
tg_service = TelegramBotService(settings.tg_api_key, settings.tg_chat_id)
sensor_service = SensorClientService()


def calculate_production(
        collection_name: str, current_value: float, speed_info: bool
) -> tuple[float, float]:
    """ Calculate the production for the shift """
    produced, speed_for_shift = 0.0, 0.0
    doc = repo.get_last_document(collection_name + "_shift_report", False)
    if doc:
        last_value = doc.get("value", 0.0)
        if current_value >= last_value:
            produced = max(0.0, current_value - last_value)
        else:
            produced = current_value
        if speed_info:
            time_diff_seconds = utils.get_time_difference(doc.get("datetime"))
            speed_for_shift = utils.calculate_speed(produced, time_diff_seconds)

    return produced, speed_for_shift


def calculate_day_production(
        collection_name: str, difference: float
) -> float:
    """ Calculate the total production for the day """
    doc = repo.get_collection(
        collection_name=collection_name, limit=1, skip=1
    )
    doc = doc[0] if doc else None
    produced = doc.get("difference", 0.0) + difference

    return produced


def get_weekly_data(collection_name: str) -> list[dict] | None:
    """ Get the data for the current week """
    start_of_week = utils.get_start_of_week()
    week_data = repo.get_collection(
        collection_name=collection_name,
        sort_by="datetime",
        query={"datetime": {
            "$gte": datetime.combine(start_of_week, datetime.min.time())
        }},
        limit=16
    )
    return week_data or None


def get_daily_data(
        collection_name: str,
        shift_start: datetime,
        shift_end: datetime
) -> list[dict] | None:
    """ Get the data for the current shift """
    daily_data = repo.get_collection(
        collection_name=collection_name.replace("_shift_report", ""),
        sort_by="datetime",
        query={"datetime": {
            "$gte": shift_start.astimezone(utils.TIMEZONE),
            "$lte": shift_end.astimezone(utils.TIMEZONE)
        }},
        limit=1000
    )
    return daily_data or None


def generate_plot(
        collection_name: str,
        job_description: str,
        shift_start: datetime,
        shift_end: datetime,
        shift_name: str
) -> list[str]:
    """ Generate the plot for the current week and shift """
    week_data = get_weekly_data(collection_name)
    daily_data = get_daily_data(collection_name, shift_start, shift_end)

    plots = []
    if week_data:
        week_data.sort(key=itemgetter("datetime"))
        for plot_func in [utils.generate_shift_plot, utils.generate_daily_plot]:
            plot_path = plot_func(week_data, job_description)
            if plot_path:
                plots.append(plot_path)

    if daily_data:
        stem_plot_path = utils.generate_stem_plot(
            daily_data, job_description, shift_name
        )
        if stem_plot_path:
            plots.append(stem_plot_path)

    return plots


def generate_multiline_plot(
        collection_name: str,
        job_description: str,
        shift_start: datetime,
        shift_end: datetime,
        shift_name: str
) -> tuple[str, str] | tuple[None, None]:
    """ Generate the multiline plot for the current shift """
    data = get_daily_data(collection_name, shift_start, shift_end)

    if not data:
        return None, None

    line_plot_path, title = utils.generate_line_plot(
        data, job_description, shift_name
    )

    return line_plot_path, title


def get_ext_data(
        collection_name: str,
        dto: schemas.TitleValueSchema,
        shift_report: bool
) -> schemas.DataSchemaExt | None:
    """ Get the extended data for the current timestamp """
    doc = repo.get_last_document(collection_name, False)
    if not doc:
        return schemas.DataSchemaExt(
            value=dto.value, difference=0.0,
            speed=0.0, metric_unit=dto.metric_unit
        )

    last_value = doc.get("value", 0.0)

    if dto.value >= last_value:
        diff = max(0.0, dto.value - last_value)
    else:
        diff = dto.value

    if diff <= 0.0 and not shift_report:
        return None

    time_diff_seconds = utils.get_time_difference(doc.get("datetime"))
    speed = utils.calculate_speed(diff, time_diff_seconds)

    return schemas.DataSchemaExt(
        value=dto.value, difference=diff,
        speed=speed, metric_unit=dto.metric_unit
    )


def store_data(
        collection_name: str,
        dto: list[schemas.TitleValueSchema],
        diff_field: bool,
        shift_report: bool = False
) -> schemas.DataSchemaExt | schemas.MultipleDataSchema | None:
    """ Store the data in the database """
    if len(dto) == 1 and diff_field:
        data = get_ext_data(collection_name, dto[0], shift_report)
    else:
        data = schemas.MultipleDataSchema(values=dto)

    if not data:
        return None

    repo.create_document(
        collection_name=collection_name,
        document=data.model_dump(),
        set_timestamp=False
    )

    return data


def _process_cumulative_report(
        collection_name: str,
        job_description: str,
        data: schemas.DataSchemaExt,
        previous: bool = False,
):
    shift_start, shift_end, shift_name = utils.calculate_shift(timedelta(hours=1), previous)
    produced_per_day = calculate_day_production(collection_name, data.difference)
    message = utils.report_message(
        shift_start, shift_end, shift_name,
        data.value, data.difference, produced_per_day,
        data.metric_unit, job_description
    )
    plots = generate_plot(
        collection_name, job_description,
        shift_start, shift_end, shift_name
    )
    tg_service.send_report_message(message, plots)


def _process_multiple_report(
        collection_name: str,
        job_description: str,
        previous: bool = False,
):
    shift_start, shift_end, shift_name = utils.calculate_shift(timedelta(hours=1), previous)
    img_path, title = generate_multiline_plot(
        collection_name, job_description,
        shift_start, shift_end, shift_name
    )
    if img_path:
        tg_service.send_report_plot(title, img_path)


def process_cumulative_data(
        collection_name: str,
        job_description: str,
        sensors: list[dict],
        tg_send: bool,
        shift_report: bool,
        speed_info: bool,
        chat: str | None
):
    sensors = [Sensor(**sensor) for sensor in sensors]
    values, is_zero, has_fault = sensor_service.read_sensors_by_id(sensors, True)
    data = store_data(collection_name, values, True, shift_report)

    if not data and tg_send:
        idle.notify_idle(collection_name, job_description, chat, has_fault)
        return
    idle.reset_counter(collection_name)

    if not shift_report:
        shift_start, _, shift_name = utils.calculate_shift()
        produced, speed_for_shift = calculate_production(
            collection_name, data.value, speed_info
        )
        produced = produced if produced > 0 else data.difference
        message = utils.production_message(
            data.speed, speed_for_shift, produced,
            data.metric_unit, shift_name, job_description,
            speed_info
        )
        tg_service.send_production_message(message, chat)
        if collection_name == "Rvo_Production_Job":
            send_rvo_data(
                shift_start, shift_name, data.speed,
                speed_for_shift, produced
            )
    else:
        _process_cumulative_report(collection_name, job_description, data)


def process_data(
        collection_name: str,
        job_description: str,
        sensors: list[dict],
        tg_send: bool,
        shift_report: bool,
        summation: bool,
        chat: str | None
):
    if not shift_report:
        _, _, shift_name = utils.calculate_shift()
        sensors = [Sensor(**sensor) for sensor in sensors]
        values, is_zero, has_fault = sensor_service.read_sensors_by_id(sensors, summation)
        doc = repo.get_last_document(collection_name)
        data = [value.model_dump() for value in values]

        if is_zero or (
                not settings.skip_eq_condition and (
                doc and doc['values'] == data
        )):
            idle.notify_idle(collection_name, job_description, chat, has_fault)
            return
        idle.reset_counter(collection_name)

        data = store_data(collection_name, values, False)

        if tg_send:
            message = utils.custom_message_template(
                data.values, shift_name, job_description
            )
            tg_service.send_production_message(message, chat)
    if shift_report and tg_send:
        _process_multiple_report(collection_name, job_description)


def send_report(
        collection_name: str,
        job_description: str,
        diff_field: bool
) -> bool:
    collection_name = re.sub(r"(_am|_pm)$", "", collection_name)
    if diff_field:
        data = repo.get_collection(
            collection_name=collection_name, limit=1, skip=0
        )
        if len(data) == 0:
            return False
        else:
            data = schemas.DataSchemaExt(**data[0])
        _process_cumulative_report(
            collection_name, job_description, data, True
        )
    else:
        _process_multiple_report(
            collection_name, job_description, True
        )
    return True
