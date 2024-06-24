import logging
from aiogram import Bot
from aiogram.enums import ParseMode

logger = logging.getLogger(__name__)


async def send_notification(bot: Bot, user_id: int, message: str, parse_mode: ParseMode = ParseMode.HTML):
    try:
        await bot.send_message(user_id, message, parse_mode=parse_mode)
        message.ch
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
