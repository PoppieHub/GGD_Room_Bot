import asyncio
from aiogram import types
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from bson import ObjectId
from datetime import datetime

from src.controller.handlers.states import RoomState
from src.models import Room, ChooseEditEnum, AnswerEnum, Map, GameMode
from src.keyboards import default_keyboard, cancel_keyboard, map_keyboard, game_mode_keyboard
from src.config import dp, rooms_collection, logger, bot
from src.utils import validate_code, validate_host
from src.tasks import LIFE_TIME, auto_delete_tasks, schedule_auto_delete, \
    reschedule_auto_delete, cancel_auto_delete


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
    room = Room(
        code=data['code'],
        host=data['host'],
        map=Map(data['map']),
        game_mode=GameMode(message.text),
        owner_id=str(message.from_user.id),
        created_at=datetime.now()
    )

    result = rooms_collection.insert_one(room.to_dict())
    room_id = result.inserted_id

    # Планирование авто-удаления
    task = asyncio.create_task(schedule_auto_delete(bot, room_id, LIFE_TIME, rooms_collection))
    auto_delete_tasks[room_id] = task

    logger.info(f"Комната: {room.code} с индификаторм: {room_id} была добавлена пользователем {message.from_user.id}")

    await state.clear()
    await message.answer(AnswerEnum.info_added_room.value, reply_markup=default_keyboard, parse_mode=ParseMode.HTML)


# Обработчики для редактирования комнаты
@dp.message(RoomState.edit)
async def choose_edit_option(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    user_id = str(message.from_user.id)
    room = rooms_collection.find_one({'owner_id': user_id, 'code': message.text})

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
    rooms_collection.update_one({'_id': room_id}, {'$set': {'code': message.text}})

    await reschedule_auto_delete(bot, room_id, rooms_collection)

    await state.clear()
    await message.answer(AnswerEnum.success_edit.value, reply_markup=default_keyboard, parse_mode=ParseMode.HTML)

    logger.info(f"Поле код комнаты {room_id} было изменено пользователем {message.from_user.id} на {message.text}")


@dp.message(RoomState.edit_host)
async def edit_host(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    if not validate_host(message.text):
        await message.answer(AnswerEnum.error_host.value, parse_mode=ParseMode.HTML)
        return

    data = await state.get_data()
    room_id = ObjectId(data['room_id'])
    rooms_collection.update_one({'_id': room_id}, {'$set': {'host': message.text}})

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
    rooms_collection.update_one({'_id': room_id}, {'$set': {'map': message.text}})

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
    rooms_collection.update_one({'_id': room_id}, {'$set': {'game_mode': message.text}})

    await reschedule_auto_delete(bot, room_id, rooms_collection)

    await state.clear()
    await message.answer(AnswerEnum.success_edit.value, reply_markup=default_keyboard, parse_mode=ParseMode.HTML)

    logger.info(f"Поле режим комнаты {room_id} было изменено пользователем {message.from_user.id} на {message.text}")


@dp.message(RoomState.confirm_delete)
async def confirm_delete(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    if message.text == "Да":
        user_id = str(message.from_user.id)
        rooms = list(rooms_collection.find({'owner_id': user_id}))

        for room in rooms:
            room_id = room['_id']
            cancel_auto_delete(room_id)  # Отмена задачи авто-удаления
            rooms_collection.delete_one({'_id': room_id})

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

    user_id = str(message.from_user.id)
    room = rooms_collection.find_one({'owner_id': user_id, 'code': message.text})

    if room:
        room_id = room['_id']
        cancel_auto_delete(room_id)  # Отмена задачи авто-удаления
        rooms_collection.delete_one({'_id': room_id})
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

    user_id = str(message.from_user.id)
    room = rooms_collection.find_one({'owner_id': user_id, 'code': message.text})

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