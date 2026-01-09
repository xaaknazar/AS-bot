import re
import pytz
import threading
import numpy as np
from itertools import groupby
from tempfile import NamedTemporaryFile

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as m_dates

from app.config import settings


TIMEZONE = pytz.timezone(settings.timezone)

matplotlib.use('Agg')
matplotlib_lock = threading.Lock()


def remove_emoji(text: str) -> str:
    regrex_pattern = re.compile(pattern = "["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
                           "]+", flags = re.UNICODE)
    return regrex_pattern.sub(r"",text)


def plot_data(
        x: list,
        y: np.ndarray,
        title: str,
        x_label: str,
        y_label: str,
        plot_type: str
) -> str:
    with matplotlib_lock:
        if plot_type == "stem":
            plt.stem(x, y, markerfmt=".")
            ax = plt.gca()
            ax.xaxis.set_major_locator(m_dates.HourLocator())
            ax.xaxis.set_major_formatter(m_dates.DateFormatter("%H:00", tz=TIMEZONE))
        if plot_type == "bar":
            plt.bar(x, y, color="orange")
            for i in range(len(x)):
                plt.text(x[i], y[i], f"{y[i]:.1f}", ha="center", va="bottom") # type: ignore
        plt.title(title)
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        plt.xticks(rotation=25)
        plt.grid()
        with NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            plt.savefig(temp_file.name)
            image_file = temp_file.name
        plt.close()

    return image_file


def plot_line_plot(
        x: list,
        y: np.ndarray,
        title: str,
        x_label: str,
        legends: list[str],
        metric_units: list[str]
) -> str:
    with matplotlib_lock:
        rows, cols = len(legends), 1
        fig, axes = plt.subplots(
            rows, cols, figsize=(10, 3 * rows), constrained_layout=True
        )
        axes = axes if rows > 1 else [axes]
        cmap = plt.get_cmap("tab10")
        for i, label in enumerate(legends):
            ax = axes[i]
            marker = "." if len(x) > 50 else "o"

            ax.plot(x, y[i], label=label, marker=marker, color=cmap(i))
            ax.xaxis.set_major_locator(m_dates.HourLocator())
            ax.xaxis.set_major_formatter(m_dates.DateFormatter("%H:00", tz=TIMEZONE))
            ax.set_ylabel(metric_units[i])
            ax.legend(loc="upper right")
            plt.xticks(rotation=25)
            ax.grid()

        plt.suptitle(title, fontsize=16)
        plt.xlabel(x_label)

        with NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            plt.savefig(temp_file.name)
            image_file = temp_file.name
        plt.close()

    return image_file


def generate_shift_plot(
        week_data: list[dict], job_description: str
) -> str | None:
    metric_unit = week_data[0]["metric_unit"]
    x = [
        doc["datetime"].astimezone(TIMEZONE).strftime("%d/%m %H")
        for doc in week_data
    ]
    y = np.array([doc["difference"] for doc in week_data])

    if y.sum() <= 0.0:
        return None

    title = f"{job_description} за неделю (по сменам)"
    img_path = plot_data(
        x, y, title,"Time", metric_unit,"bar"
    )

    return img_path


def generate_daily_plot(
        week_data: list[dict], job_description: str
) -> str | None:
    metric_unit = week_data[0]["metric_unit"]
    grouped_data = groupby(
        week_data, key=lambda item: item["datetime"].date()
    )
    daily_sums = [
        (day, sum(item["difference"] for item in items))
        for day, items in grouped_data
    ]
    x = [day.strftime("%d/%m") for day, _ in daily_sums]
    y = np.array([total for _, total in daily_sums])

    if y.sum() <= 0.0:
        return None

    title = f"{job_description} за неделю (по дням)"
    img_path = plot_data(
        x, y, title, "Time", metric_unit, "bar"
    )

    return img_path


def generate_stem_plot(
        data: list[dict], job_description: str, shift_name: str
) -> str | None:
    metric_unit = data[0]["metric_unit"]
    x = [doc["datetime"] for doc in data]
    y = np.array([doc["difference"] for doc in data])

    if y.sum() <= 0.0:
        return None

    title = f"{job_description} за день ({shift_name} cмена)"
    img_path = plot_data(
        x, y, title, "Time", metric_unit, "stem"
    )

    return img_path


def generate_line_plot(
        data: list[dict], job_description: str, shift_name: str
) -> tuple[str, str] |  tuple[None, None]:
    legends = [entry["title"] for entry in data[0]["values"]]
    metric_units = [entry["metric_unit"] for entry in data[0]["values"]]

    x = [doc["datetime"] for doc in data]
    y = np.zeros((len(data), len(legends)))

    for i, dto in enumerate(data):
        values_dict = {v["title"]: v["value"] for v in dto["values"]}
        y[i] = [values_dict.get(title, 0.0) for title in legends]

    if y.sum() == 0.0:
        return None, None

    legends = list(map(remove_emoji, legends))
    title = f"{job_description} за день ({shift_name} cмена)"
    img_path = plot_line_plot(
        x, y.T, title, "Time", legends, metric_units
    )

    return img_path, title
