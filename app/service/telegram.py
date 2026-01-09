import os
import time
import logging

from telebot import TeleBot
from telebot.types import InputMediaPhoto, InputFile
from telebot.apihelper import ApiTelegramException

from app.config import settings


def retry_on_rate_limit(func):
    def wrapper(self, *args, max_retries: int = 3, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(self, *args, **kwargs)
            except ApiTelegramException as e:
                if e.error_code == 429:
                    sleep_time = int(
                        e.result_json
                        .get("parameters", {})
                        .get("retry_after", 5)
                    )
                    logging.warning(f"Rate limit exceeded."
                                    f" Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    raise
        return None
    return wrapper


class TelegramBotService:
    def __init__(self, token: str, chat_id: int):
        self.bot = TeleBot(token)
        self.tg_chat_id = chat_id
        self.report_thread = settings.tg_report_id
        self.threads = {
            "production": settings.tg_prod_id,
            "monitoring": settings.tg_monitor_id,
            "technology": settings.tg_tech_id,
            "core_shop": settings.tg_core_id,
            "rvo": settings.tg_rvo_id,
        }
        # self.report_thread = settings.tg_test_id
        # self.threads = {
        #     thread: settings.tg_test_id
        #     for thread in self.threads.keys()
        # }

    @retry_on_rate_limit
    def send_text_message(self, text: str, thread_id: int | None) -> None:
        self.bot.send_message(
            chat_id=self.tg_chat_id,
            text=text,
            message_thread_id=thread_id,
            parse_mode="HTML"
        )

    @retry_on_rate_limit
    def send_photo(self, image_path: str, caption: str, thread_id: int | None) -> None:
        self.bot.send_photo(
            chat_id=self.tg_chat_id,
            photo=InputFile(image_path),
            caption=caption,
            message_thread_id=thread_id,
            parse_mode="HTML"
        )
        os.remove(image_path)

    @retry_on_rate_limit
    def send_report_message(self, text: str, images: list[str] | None) -> None:
        if images:
            media_group = [
                InputMediaPhoto(media=InputFile(image), parse_mode="HTML")
                for image in images
            ]
            media_group[0].caption = text
            self.bot.send_media_group(
                chat_id=self.tg_chat_id,
                media=media_group,
                message_thread_id=self.report_thread
            )
            for image in images:
                os.remove(image)
        else:
            self.send_text_message(text, self.report_thread)

    def send_report_plot(self, caption: str, image: str) -> None:
        self.send_photo(image, caption, self.report_thread)

    def send_production_message(self, text: str, chat: str | None) -> None:
        if chat in self.threads:
            self.send_text_message(text, self.threads[chat])
        else:
            self.send_text_message(text, None)
