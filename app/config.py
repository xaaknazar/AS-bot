import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_url: str
    mongodb_db: str
    mongodb_sensors_db: str

    timezone: str
    first_shift: str
    second_shift: str

    tg_api_key: str
    tg_chat_id: int

    tg_report_id: int
    tg_prod_id: int
    tg_monitor_id: int
    tg_tech_id: int
    tg_core_id: int
    tg_test_id: int
    tg_rvo_id: int

    skip_eq_condition: bool

    model_config = SettingsConfigDict(extra="allow", env_file=".env")

    def get_settings(self):
        return {
            'first_shift': self.first_shift,
            'second_shift': self.second_shift,
            'timezone': self.timezone,
            'skip_eq_condition': self.skip_eq_condition
        }


settings = Settings() # type: ignore


def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,  # type: ignore
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:     %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logging.getLogger("opcua").setLevel(logging.ERROR)
    logging.getLogger("snap7").setLevel(logging.WARNING)
    logging.getLogger("pymodbus").setLevel(logging.WARNING)
    logging.getLogger("telebot").setLevel(logging.WARNING)
