from datetime import datetime
from prettytable import PrettyTable
from pydantic import BaseModel


class TitleValueSchema(BaseModel):
    title: str
    value: float
    metric_unit: str


def report_message(
        shift_start: datetime,
        shift_end: datetime,
        shift_name: str,
        value: float,
        production: float,
        produced_per_day: float,
        metric_unit: str,
        job_description: str
) -> str:
    metric_symbol = metric_unit[0]
    rows = [
        ("Произведено", f"{round(production, 1)}{metric_symbol}"),
        ("Счетчик", f"{round(value, 1)}{metric_symbol}")
    ]
    if shift_name == "Ночная ☾":
        rows.insert(1,(
            "За сутки", f"{round(produced_per_day, 1)}{metric_symbol}"
        ))

    table = PrettyTable()
    table.field_names = ["Смена", shift_name]
    table.add_rows(rows) # type: ignore
    message = (
        f"<b>{job_description} 📊 </b>\n"
        f"<u>Отчет за смену</u>\n"
        f"🗓<i>️{shift_start.strftime('%d.%m.%Y %H:%M')}</i>\n"
        f"🗓<i>️{shift_end.strftime('%d.%m.%Y %H:%M')}</i>\n"
        f"<pre>{table}</pre>"
    )

    return message


def production_message(
        speed: float,
        speed_for_shift: float,
        produced: float,
        metric_unit: str,
        shift_name: str,
        job_description: str,
        speed_info: bool
) -> str:
    metric_symbol = metric_unit[0]
    rows = [
        ("Произведено", f"{round(produced, 1)}{metric_symbol}")
    ]
    if speed_info:
        rows.insert(
            0,
            ("Произ-ть", f"{round(speed, 1)}{metric_symbol}/ч")
        )
    if speed_for_shift > 0:
        rows.insert(
            1,
            ("Произ-ть за смену",
             f"{round(speed_for_shift, 1)}{metric_symbol}/ч")
        )

    table = PrettyTable()
    table.field_names = [shift_name, "Значение"]
    table.add_rows(rows) # type: ignore

    message = (
        f"<b>{job_description} 📈</b>\n"
        f"<pre>{table}</pre>"
    )

    return message


def custom_message_template(
        dtos: list[TitleValueSchema],
        shift_name: str,
        job_description: str
) -> str:
    rows = [
        (dto.title, f'{round(dto.value, 1)}{dto.metric_unit[0]}')
        for dto in dtos
    ]

    table = PrettyTable()
    table.field_names = [shift_name, "Значение"]
    table.add_rows(rows) # type: ignore

    message = (
        f"<b>{job_description} ⚡️️</b>\n"
        f"<pre>{table}</pre>"
    )

    return message
