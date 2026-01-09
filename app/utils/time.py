import pytz
from datetime import time as time_
from datetime import datetime, timedelta, date

from app.config import settings


TIMEZONE = pytz.timezone(settings.timezone)


def current_datetime() -> datetime:
    return datetime.now(tz=TIMEZONE)


def get_shift_times() -> tuple[tuple[int, int], tuple[int, int]]:
    first_shift = datetime.strptime(
        settings.first_shift, "%H:%M"
    ).time()
    second_shift = datetime.strptime(
        settings.second_shift, "%H:%M"
    ).time()
    return (
        (first_shift.hour, first_shift.minute),
        (second_shift.hour, second_shift.minute)
    )


def calculate_shift(
        time_delta: timedelta = timedelta(minutes=0),
        previous: bool = False
) -> tuple[datetime, datetime, str]:
    time_delta = time_delta if not previous else timedelta(minutes=0)
    now = current_datetime() - time_delta
    first_shift, second_shift = get_shift_times()
    if time_(first_shift[0], first_shift[1]) <= now.time() < time_(second_shift[0], second_shift[1]):
        if not previous:
            shift_start_time = now.replace(hour=first_shift[0], minute=first_shift[1])
            shift_end_time = shift_start_time.replace(hour=second_shift[0], minute=second_shift[1])
            shift_name = "Дневная ☀︎"
        else:
            shift_end_time = now.replace(hour=first_shift[0], minute=first_shift[1])
            shift_start_time = shift_end_time.replace(hour=second_shift[0], minute=second_shift[1]) - timedelta(days=1)
            shift_name = "Ночная ☾"
    else:
        if not previous:
            shift_start_time = now.replace(hour=second_shift[0], minute=second_shift[1])
            if now.time() < time_(first_shift[0], first_shift[1]):
                shift_start_time -= timedelta(days=1)
            shift_end_time = shift_start_time.replace(hour=first_shift[0]) + timedelta(days=1)
            shift_name = "Ночная ☾"
        else:
            shift_end_time = now.replace(hour=second_shift[0], minute=second_shift[1])
            if now.time() < time_(first_shift[0], first_shift[1]):
                shift_end_time -= timedelta(days=1)
            shift_start_time = shift_end_time.replace(hour=first_shift[0])
            shift_name = "Дневная ☀︎"
    return shift_start_time, shift_end_time, shift_name


def get_start_of_week() -> date:
    now = current_datetime()
    return now.date() - timedelta(days=now.weekday())


def get_time_difference(last_datetime: datetime) -> float:
    now = current_datetime()
    last_datetime = last_datetime.astimezone(tz=TIMEZONE)
    return (now - last_datetime).total_seconds()

def calculate_speed(diff: float, time_diff_seconds: float) -> float:
    if time_diff_seconds > 0:
        return (3600 / time_diff_seconds) * diff
    return 0.0
