import logging
from collections import defaultdict

from app.service.telegram import TelegramBotService
from app.config import settings


idle_counter = defaultdict(int)
tg_service = TelegramBotService(settings.tg_api_key, settings.tg_chat_id)


def notify_idle(
        collection_name: str,
        job_description: str,
        chat: str | None,
        has_fault: bool
) -> None:
    """ Notify about the idle state of the job """
    idle_counter[collection_name] += 1
    counter = idle_counter[collection_name]
    if counter == 3:
        if has_fault:
            tg_service.send_production_message(
                f"⚠️ ВНИМАНИЕ: <b>{job_description}</b> в состоянии неисправности!",
                chat
            )
            logging.warning(f"{collection_name} is in fault state!")
            return
        else:
            tg_service.send_production_message(
                f"ℹ️ <b>{job_description}</b> находится в режиме ожидания 💤.",
                chat
            )
            logging.warning(f"{collection_name} is idle!")


def reset_counter(collection_name: str) -> None:
    if collection_name in idle_counter:
        idle_counter.pop(collection_name, None)
        logging.info(f"Idle counter for {collection_name} was reset.")
