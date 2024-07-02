import asyncio
from aiogram import types
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from bson import ObjectId
from datetime import datetime

from src.controller.handlers.states import RoomState, AdminState
from src.models import Room, ChooseEditEnum, AnswerEnum, Map, GameMode, Chat, User
from src.keyboards import default_keyboard, cancel_keyboard, map_keyboard, game_mode_keyboard
from src.config import dp, rooms_collection, logger, bot, users_collection, chats_collection
from src.utils import validate_code, validate_host, get_user, get_chat
from src.tasks import LIFE_TIME, auto_delete_tasks, schedule_auto_delete, \
    reschedule_auto_delete, cancel_auto_delete
from src.notifications import send_notification


async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(AnswerEnum.we_have_cancel.value, reply_markup=default_keyboard, parse_mode=ParseMode.HTML)


# Утилита для нажатия отмены
async def is_press_cancel(message: types.Message, state: FSMContext) -> bool:
    if message.text == "Отмена":
        await cancel(message, state)

        return True


# Обработчики для добавления комнаты
@dp.message(RoomState.code)
async def process_code(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    if not validate_code(message.text):
        await message.answer(AnswerEnum.error_code.value, parse_mode=ParseMode.HTML)
        return

    await state.update_data(code=message.text)
    await message.answer(AnswerEnum.choose_host.value, reply_markup=cancel_keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(RoomState.host)


@dp.message(RoomState.host)
async def process_host(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    if not validate_host(message.text):
        await message.answer(AnswerEnum.error_host.value, parse_mode=ParseMode.HTML)
        return

    await state.update_data(host=message.text)
    await message.answer(AnswerEnum.choose_map.value, reply_markup=map_keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(RoomState.map)


@dp.message(RoomState.map)
async def process_map(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    # Проверка на соответствие предложенным значениям клавиатуры
    if message.text not in [button.value for button in Map]:
        await message.answer(AnswerEnum.invalid_option.value, reply_markup=map_keyboard, parse_mode=ParseMode.HTML)
        return

    await state.update_data(map=message.text)
    await message.answer(AnswerEnum.choose_game_mode.value, reply_markup=game_mode_keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(RoomState.game_mode)


@dp.message(RoomState.game_mode)
async def process_game_mode(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    # Проверка на соответствие предложенным значениям клавиатуры
    if message.text not in [button.value for button in GameMode]:
        await message.answer(AnswerEnum.invalid_option.value, reply_markup=game_mode_keyboard, parse_mode=ParseMode.HTML)
        return

    data = await state.get_data()

    user_data = await get_user(message.from_user.id)
    chat_data = await get_chat(message.chat.id)

    room = Room(
        code=data['code'],
        host=data['host'],
        map=Map(data['map']),
        game_mode=GameMode(message.text),
        owner=user_data,
        chat=chat_data,
        created_at=datetime.now()
    )

    result = await rooms_collection.insert_one(room.to_dict())
    room_id = result.inserted_id

    # Планирование авто-удаления
    task = asyncio.create_task(schedule_auto_delete(bot, room_id, LIFE_TIME, rooms_collection))
    auto_delete_tasks[room_id] = task

    logger.info(f"Комната: {room.code} с индификаторм: {room_id} была добавлена пользователем {message.from_user.id}")

    await state.clear()
    await message.answer(AnswerEnum.info_added_room.value, reply_markup=default_keyboard, parse_mode=ParseMode.HTML)

    # Отправляем уведомления всем подписчикам
    for chat in user_data.subscribers:
        await send_notification(bot, chat.chat_id, (
            f"🔔 <b>Уведомление об добавлении комнаты</b> 🔔\n\n"
            f"Пользователь с ником <b>{room.host}</b> опубликовал комнату с кодом: <code>{room.code}</code>\n\n"
            f"Вы получили это уведомление, потому что вы подписаны на обновления этого пользователя"
        ))


# Обработчики для редактирования комнаты
@dp.message(RoomState.edit)
async def choose_edit_option(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    user = await get_user(message.from_user.id)
    room = await rooms_collection.find_one({'owner': user.to_dict(), 'code': message.text})

    if room is None:
        await message.answer(AnswerEnum.not_found.value, reply_markup=default_keyboard, parse_mode=ParseMode.HTML)
        await state.clear()
        return

    buttons = [types.KeyboardButton(text=item.value) for item in ChooseEditEnum] + [types.KeyboardButton(text="Отмена")]

    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 2] for i in range(0, len(buttons), 2)],
        resize_keyboard=True
    )

    await message.answer(AnswerEnum.choose_edit.value, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.update_data(room_id=str(room['_id']))
    await state.set_state(RoomState.edit_option)


@dp.message(RoomState.edit_option)
async def edit_option(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    option = message.text
    state_dict = {
        ChooseEditEnum.code.value: RoomState.edit_code,
        ChooseEditEnum.host.value: RoomState.edit_host,
        ChooseEditEnum.map.value: RoomState.edit_map,
        ChooseEditEnum.game_mode.value: RoomState.edit_game_mode
    }

    if option not in state_dict:
        await message.answer(AnswerEnum.error_edit.value, reply_markup=default_keyboard, parse_mode=ParseMode.HTML)
        await state.clear()
        return

    if option == ChooseEditEnum.map.value:
        await message.answer(f"Установите новую карту:", reply_markup=map_keyboard, parse_mode=ParseMode.HTML)
    elif option == ChooseEditEnum.game_mode.value:
        await message.answer(f"Установите новый режим:", reply_markup=game_mode_keyboard, parse_mode=ParseMode.HTML)
    else:
        await message.answer(f"Установите новое значение для поля '{option}':", reply_markup=cancel_keyboard, parse_mode=ParseMode.HTML)

    await state.set_state(state_dict[option])


@dp.message(RoomState.edit_code)
async def edit_code(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    if not validate_code(message.text):
        await message.answer(AnswerEnum.error_code.value, parse_mode=ParseMode.HTML)
        return

    data = await state.get_data()
    room_id = ObjectId(data['room_id'])
    await rooms_collection.update_one({'_id': room_id}, {'$set': {'code': message.text}})
    room_data = await rooms_collection.find_one({'_id': room_id})
    room = Room.from_dict(room_data)

    await reschedule_auto_delete(bot, room_id, rooms_collection)

    await state.clear()
    await message.answer(AnswerEnum.success_edit.value, reply_markup=default_keyboard, parse_mode=ParseMode.HTML)

    logger.info(f"Поле код комнаты {room_id} было изменено пользователем {message.from_user.id} на {message.text}")

    # Отправляем уведомления всем подписчикам
    for chat in room.owner.subscribers:
        await send_notification(bot, chat.chat_id, (
            f"🔔 <b>Уведомление об изменении комнаты</b> 🔔\n\n"
            f"Пользователь с ником <b>{room.host}</b> изменил код: <code>{room.code}</code>\n\n"
            f"Вы получили это уведомление, потому что вы подписаны на обновления этого пользователя"
        ))


@dp.message(RoomState.edit_host)
async def edit_host(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    if not validate_host(message.text):
        await message.answer(AnswerEnum.error_host.value, parse_mode=ParseMode.HTML)
        return

    data = await state.get_data()
    room_id = ObjectId(data['room_id'])
    await rooms_collection.update_one({'_id': room_id}, {'$set': {'host': message.text}})

    await reschedule_auto_delete(bot, room_id, rooms_collection)

    await state.clear()
    await message.answer(AnswerEnum.success_edit.value, reply_markup=default_keyboard, parse_mode=ParseMode.HTML)

    logger.info(f"Поле хост комнаты {room_id} было изменено пользователем {message.from_user.id} на {message.text}")


@dp.message(RoomState.edit_map)
async def edit_map(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    if message.text not in [button.value for button in Map]:
        await message.answer(AnswerEnum.error_edit.value, reply_markup=map_keyboard, parse_mode=ParseMode.HTML)
        return

    data = await state.get_data()
    room_id = ObjectId(data['room_id'])
    await rooms_collection.update_one({'_id': room_id}, {'$set': {'map': message.text}})

    await reschedule_auto_delete(bot, room_id, rooms_collection)

    await state.clear()
    await message.answer(AnswerEnum.success_edit.value, reply_markup=default_keyboard, parse_mode=ParseMode.HTML)

    logger.info(f"Поле карта комнаты {room_id} было изменено пользователем {message.from_user.id} на {message.text}")


@dp.message(RoomState.edit_game_mode)
async def edit_game_mode(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    if message.text not in [button.value for button in GameMode]:
        await message.answer(AnswerEnum.error_edit.value, reply_markup=game_mode_keyboard, parse_mode=ParseMode.HTML)
        return

    data = await state.get_data()
    room_id = ObjectId(data['room_id'])
    await rooms_collection.update_one({'_id': room_id}, {'$set': {'game_mode': message.text}})

    await reschedule_auto_delete(bot, room_id, rooms_collection)

    await state.clear()
    await message.answer(AnswerEnum.success_edit.value, reply_markup=default_keyboard, parse_mode=ParseMode.HTML)

    logger.info(f"Поле режим комнаты {room_id} было изменено пользователем {message.from_user.id} на {message.text}")


@dp.message(RoomState.confirm_delete)
async def confirm_delete(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    if message.text == "Да":
        user = await get_user(message.from_user.id)
        rooms = await rooms_collection.find({'owner': user.to_dict()}).to_list(length=None)

        for room in rooms:
            room_id = room['_id']
            cancel_auto_delete(room_id)  # Отмена задачи авто-удаления
            await rooms_collection.delete_one({'_id': room_id})

        await message.answer(AnswerEnum.room_delite_plus.value, parse_mode=ParseMode.HTML, reply_markup=types.ReplyKeyboardRemove())
        await message.answer(AnswerEnum.choose_code.value, reply_markup=cancel_keyboard, parse_mode=ParseMode.HTML)
        await state.set_state(RoomState.code)
        logger.info(f"Комната пользователя {message.from_user.id} была удалена пользователем")
    else:
        await cancel(message, state)


@dp.message(RoomState.delete)
async def process_delete(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    user = await get_user(message.from_user.id)
    room = await rooms_collection.find_one({'owner': user.to_dict(), 'code': message.text})

    if room:
        room_id = room['_id']
        cancel_auto_delete(room_id)  # Отмена задачи авто-удаления
        await rooms_collection.delete_one({'_id': room_id})
        logger.info(f"Комната: {message.text} с индификатором {room_id} была удалена пользователем {message.from_user.id}")
    else:
        await message.answer(AnswerEnum.invalid_option.value, parse_mode=ParseMode.HTML)
        await state.set_state(RoomState.delete)
        return

    await state.clear()
    await message.answer(AnswerEnum.room_delite.value, reply_markup=default_keyboard, parse_mode=ParseMode.HTML)


@dp.message(RoomState.update)
async def process_update_room(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    user = await get_user(message.from_user.id)
    room = await rooms_collection.find_one({'owner': user.to_dict(), 'code': message.text})

    if not room:
        await message.answer(AnswerEnum.not_found.value, reply_markup=default_keyboard, parse_mode=ParseMode.HTML)
        await state.clear()
        return

    room_id = room['_id']

    # Перепланирование авто-удаления
    await reschedule_auto_delete(bot, room_id, rooms_collection)

    await state.clear()
    await message.answer(f"Время жизни комнаты с кодом <code>{message.text}</code> было обновлено.", parse_mode=ParseMode.HTML, reply_markup=default_keyboard)

    logger.info(f"Время жизни комнаты {message.text} с индификатором {room_id} было обновлено пользователем {message.from_user.id}")


@dp.message(AdminState.add_admin)
async def process_add_admin(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    if not message.text.isdigit():
        await message.reply("Пожалуйста, отправьте корректный id пользователя.")
        await state.set_state(AdminState.add_admin)
        return

    user = await get_user(int(message.text))

    if user.is_admin:
        await message.answer("Этот пользователь уже является администратором.", reply_markup=default_keyboard)
    else:
        await users_collection.update_one(user.to_dict(), {'$set': {"is_admin": True}})
        await message.answer(f"Пользователь с id <code>{user.user_id}</code> назначен администратором.",
                             parse_mode=ParseMode.HTML,
                             reply_markup=default_keyboard)
    await state.clear()


async def remove_admin(user: User):
    result = await users_collection.update_one(user.to_dict(), {'$set': {"is_admin": False}})
    return result.matched_count > 0


@dp.message(AdminState.del_admin)
async def process_remove_admin(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    if not message.text.isdigit():
        await message.reply("Пожалуйста, отправьте корректный id пользователя.")
        await state.set_state(AdminState.del_admin)
        return

    user = await get_user(int(message.text))

    if await remove_admin(user):
        await message.reply(f"Пользователь с id <code>{user.user_id}</code> удален из администраторов.",
                            reply_markup=default_keyboard,
                            parse_mode=ParseMode.HTML)
    else:
        await message.reply(f"Пользователь с id <code>{user.user_id}</code> не найден в списке администраторов.",
                            reply_markup=default_keyboard,
                            parse_mode=ParseMode.HTML)
    await state.clear()


@dp.message(AdminState.delete_room)
async def process_admin_delete_room(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    room = await rooms_collection.find_one({'code': message.text})

    if room:
        room_id = room['_id']
        cancel_auto_delete(room_id)  # Отмена задачи авто-удаления
        await rooms_collection.delete_one({'_id': room_id})
        logger.info(f"Комната: {message.text} с индификатором {room_id} была удалена пользователем {message.from_user.id}")
    else:
        await message.answer(AnswerEnum.invalid_option.value, parse_mode=ParseMode.HTML)
        await state.set_state(RoomState.delete)
        return

    await state.clear()
    await message.answer(AnswerEnum.room_delite.value, reply_markup=default_keyboard, parse_mode=ParseMode.HTML)


@dp.message(AdminState.broadcast_text)
async def process_broadcast_text(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    if not message.text:
        await message.answer("Вы не указали текст для отправки, отправьте снова", reply_markup=default_keyboard)
        await state.set_state(AdminState.broadcast_text)
        return

    # Отправляем всем пользователям, которые зарегистрировались в боте
    async for chat in chats_collection.find():
        chat = Chat.from_dict(chat)
        await send_notification(bot, chat.chat_id, message.text)

    await state.clear()
    await message.reply("Сообщения были успешно отправлены всем пользователям бота", reply_markup=default_keyboard)

