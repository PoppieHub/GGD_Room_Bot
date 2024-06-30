import asyncio
import logging
from aiogram import Bot
from datetime import datetime
from src.notifications import send_notification
from src.models import Room

logger = logging.getLogger(__name__)

LIFE_TIME = 60 * 60 * 2
NOTIFY_TIME = 60 * 5

# Для хранения задач на авто-удаление
auto_delete_tasks = {}


# Функция для автоматического удаления комнаты
async def auto_delete_room(bot: Bot, room_id, rooms_collection):
    room_data = await rooms_collection.find_one({'_id': room_id})

    if room_data:
        room = Room.from_dict(room_data)

        await rooms_collection.delete_one({'_id': room_id})
        auto_delete_tasks.pop(room_id, None)

        logger.info(f"Комната {room_id} была удалена автоматически")

        await send_notification(
            bot,
            room.chat.chat_id,
            f"🔔 <b>Уведомление об удалении комнаты</b> 🔔\n\n"
            f"Ваша комната с кодом <code>{room.code}</code> была автоматически удалена из-за истечения времени.\n\n"
            f"Не поняли, как это произошло? Ознакомьтесь с разделами /help и /rules о команде <code>/update</code>."
        )


# Функция для отправки предупреждения и последующего удаления комнаты
async def send_warning_and_delete(bot: Bot, room_id, delay, rooms_collection):
    if delay > NOTIFY_TIME:
        await asyncio.sleep(delay - NOTIFY_TIME)
        room_data = await rooms_collection.find_one({'_id': room_id})

        if room_data:
            room = Room.from_dict(room_data)

            await send_notification(
                bot,
                room.chat.chat_id,
                f"⏳ <b>Предупреждение об удалении</b> ⏳\n\n"
                f"Ваша комната с кодом <code>{room.code}</code> будет автоматически удалена через {NOTIFY_TIME / 60} минут.\n\n"
                f"Если хотите продлить срок действия комнаты, используйте команду /update"
            )
        await asyncio.sleep(NOTIFY_TIME)
    else:
        await asyncio.sleep(delay)

    await auto_delete_room(bot, room_id, rooms_collection)


# Функция для планирования авто-удаления
async def schedule_auto_delete(bot: Bot, room_id, delay, rooms_collection):
    logger.info(f"Запланировано удаление комнаты {room_id} через {delay} секунд")
    await send_warning_and_delete(bot, room_id, delay, rooms_collection)


#  Функция для отмены авто-удаления
def cancel_auto_delete(room_id):
    task = auto_delete_tasks.pop(room_id, None)
    if task:
        task.cancel()
        logger.info(f"Авто-удаление комнаты {room_id} была отменена, т.к пользователь сам удалил")


# Функция для перепланирования авто-удаления
async def reschedule_auto_delete(bot: Bot, room_id, rooms_collection):
    cancel_auto_delete(room_id)
    task = asyncio.create_task(schedule_auto_delete(bot, room_id, LIFE_TIME, rooms_collection))
    auto_delete_tasks[room_id] = task
    logger.info(f"Авто-удаление комнаты {room_id} была перепланирована, т.к пользователь обновил время жизни")


# Функция для восстановления задач авто-удаления
async def restore_auto_deletion_tasks(bot: Bot, rooms_collection):
    current_time = datetime.now()
    logger.info("Восстановление задач авто-удаления при запуске")

    async for room in rooms_collection.find():
        created_at = room['created_at']
        elapsed_time = (current_time - created_at).total_seconds()
        remaining_time = LIFE_TIME - elapsed_time

        if remaining_time <= 0:
            await rooms_collection.delete_one({'_id': room['_id']})
            logger.info(f"Комната {room['_id']} была удалена из-за истечения времени, после перезапуска")
        else:
            task = asyncio.create_task(schedule_auto_delete(bot, room['_id'], remaining_time, rooms_collection))
            auto_delete_tasks[room['_id']] = task
            logger.info(f"Восстановлено удаление комнаты {room['_id']} через {remaining_time} секунд")
