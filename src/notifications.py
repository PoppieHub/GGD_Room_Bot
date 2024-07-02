import logging
from aiogram import Bot
from aiogram.enums import ParseMode

logger = logging.getLogger(__name__)


async def send_notification(bot: Bot, chat_id: int, message: str, parse_mode: ParseMode = ParseMode.HTML):
    try:
        await bot.send_message(chat_id=chat_id, text=message, parse_mode=parse_mode)
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение пользователю {chat_id}: {e}")