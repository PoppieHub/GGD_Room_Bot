import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from dotenv import dotenv_values
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId

from src.models import Room, ChooseEditEnum, AnswerEnum
from src.utils import get_content_file, validate_code, validate_host
from src.keyboards import *
from src.tasks import LIFE_TIME, auto_delete_tasks, schedule_auto_delete, \
    reschedule_auto_delete, cancel_auto_delete, restore_auto_deletion_tasks

# Настройка логгирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Добавление FileHandler для записи логов в файл
file_handler = logging.FileHandler('bot.log')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Инициализация токена
TOKEN = dotenv_values(".env")["API_TOKEN"]
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

mongo_client = MongoClient("mongodb://ggd_bot_db:27017/")
db = mongo_client['ggd']
rooms_collection = db['rooms']


class RoomState(StatesGroup):
    code = State()
    host = State()
    map = State()
    game_mode = State()
    delete = State()
    confirm_delete = State()
    edit = State()
    edit_option = State()
    edit_code = State()
    edit_host = State()
    edit_map = State()
    edit_game_mode = State()
    update = State()


async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(AnswerEnum.we_have_cancel.value, reply_markup=default_keyboard)


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
        await message.answer(AnswerEnum.error_code.value, parse_mode="HTML")
        return

    await state.update_data(code=message.text)
    await message.answer(AnswerEnum.choose_host.value, reply_markup=cancel_keyboard)
    await state.set_state(RoomState.host)


@dp.message(RoomState.host)
async def process_host(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    if not validate_host(message.text):
        await message.answer(AnswerEnum.error_host.value, parse_mode="HTML")
        return

    await state.update_data(host=message.text)
    await message.answer(AnswerEnum.choose_map.value, reply_markup=map_keyboard)
    await state.set_state(RoomState.map)


@dp.message(RoomState.map)
async def process_map(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    # Проверка на соответствие предложенным значениям клавиатуры
    if message.text not in [button.value for button in Map]:
        await message.answer(AnswerEnum.error_edit.value, reply_markup=map_keyboard)
        return

    await state.update_data(map=message.text)
    await message.answer(AnswerEnum.choose_game_mode.value, reply_markup=game_mode_keyboard)
    await state.set_state(RoomState.game_mode)


@dp.message(RoomState.game_mode)
async def process_game_mode(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    # Проверка на соответствие предложенным значениям клавиатуры
    if message.text not in [button.value for button in GameMode]:
        await message.answer(AnswerEnum.error_edit.value, reply_markup=game_mode_keyboard)
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
    await message.answer(AnswerEnum.info_added_room.value, reply_markup=default_keyboard)


# Обработчики для редактирования комнаты
@dp.message(RoomState.edit)
async def choose_edit_option(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    user_id = str(message.from_user.id)
    room = rooms_collection.find_one({'owner_id': user_id, 'code': message.text})

    if room is None:
        await message.answer(AnswerEnum.not_found.value, reply_markup=default_keyboard)
        return

    buttons = [types.KeyboardButton(text=item.value) for item in ChooseEditEnum] + [types.KeyboardButton(text="Отмена")]

    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 2] for i in range(0, len(buttons), 2)],
        resize_keyboard=True
    )

    await message.answer(AnswerEnum.choose_edit.value, reply_markup=keyboard)
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
        await message.answer(AnswerEnum.not_found.value)
        return

    if option == ChooseEditEnum.map.value:
        await message.answer(f"Установите новую карту:", reply_markup=map_keyboard)
    elif option == ChooseEditEnum.game_mode.value:
        await message.answer(f"Установите новый режим:", reply_markup=game_mode_keyboard)
    else:
        await message.answer(f"Установите новое значение для поля '{option}':", reply_markup=cancel_keyboard)

    await state.set_state(state_dict[option])


@dp.message(RoomState.edit_code)
async def edit_code(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    if not validate_code(message.text):
        await message.answer(AnswerEnum.error_code.value)
        return

    data = await state.get_data()
    room_id = ObjectId(data['room_id'])
    rooms_collection.update_one({'_id': room_id}, {'$set': {'code': message.text}})

    await reschedule_auto_delete(bot, room_id, rooms_collection)

    await state.clear()
    await message.answer(AnswerEnum.success_edit.value, reply_markup=default_keyboard)

    logger.info(f"Поле код комнаты {room_id} было изменено пользователем {message.from_user.id} на {message.text}")


@dp.message(RoomState.edit_host)
async def edit_host(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    if not validate_host(message.text):
        await message.answer(AnswerEnum.error_host.value)
        return

    data = await state.get_data()
    room_id = ObjectId(data['room_id'])
    rooms_collection.update_one({'_id': room_id}, {'$set': {'host': message.text}})

    await reschedule_auto_delete(bot, room_id, rooms_collection)

    await state.clear()
    await message.answer(AnswerEnum.success_edit.value, reply_markup=default_keyboard)

    logger.info(f"Поле хост комнаты {room_id} было изменено пользователем {message.from_user.id} на {message.text}")


@dp.message(RoomState.edit_map)
async def edit_map(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    if message.text not in [button.value for button in Map]:
        await message.answer(AnswerEnum.error_edit.value, reply_markup=map_keyboard)
        return


    data = await state.get_data()
    room_id = ObjectId(data['room_id'])
    rooms_collection.update_one({'_id': room_id}, {'$set': {'map': message.text}})

    await reschedule_auto_delete(bot, room_id, rooms_collection)

    await state.clear()
    await message.answer(AnswerEnum.success_edit.value, reply_markup=default_keyboard)

    logger.info(f"Поле карта комнаты {room_id} было изменено пользователем {message.from_user.id} на {message.text}")


@dp.message(RoomState.edit_game_mode)
async def edit_game_mode(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    if message.text not in [button.value for button in GameMode]:
        await message.answer(AnswerEnum.error_edit.value, reply_markup=game_mode_keyboard)
        return

    data = await state.get_data()
    room_id = ObjectId(data['room_id'])
    rooms_collection.update_one({'_id': room_id}, {'$set': {'game_mode': message.text}})

    await reschedule_auto_delete(bot, room_id, rooms_collection)

    await state.clear()
    await message.answer(AnswerEnum.success_edit.value, reply_markup=default_keyboard)

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

        await message.answer(AnswerEnum.room_delite_plus.value, parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
        await message.answer(AnswerEnum.choose_code.value, reply_markup=cancel_keyboard)
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

    await state.clear()
    await message.answer(AnswerEnum.room_delite.value, reply_markup=default_keyboard)


@dp.message(Command("update"))
async def update_room(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    user_rooms = list(rooms_collection.find({'owner_id': user_id}))

    if not user_rooms:
        await message.answer(AnswerEnum.not_found.value)
        return

    buttons = [types.KeyboardButton(text=room['code']) for room in user_rooms]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 3] for i in range(0, len(buttons), 3)],
        resize_keyboard=True
    )
    keyboard.keyboard.append([types.KeyboardButton(text="Отмена")])

    await message.answer(AnswerEnum.choose_room.value, reply_markup=keyboard)
    await state.set_state(RoomState.update)


@dp.message(RoomState.update)
async def process_update_room(message: types.Message, state: FSMContext):
    if await is_press_cancel(message, state):
        return

    user_id = str(message.from_user.id)
    room = rooms_collection.find_one({'owner_id': user_id, 'code': message.text})

    if not room:
        await message.answer(AnswerEnum.not_found.value, reply_markup=default_keyboard)
        return

    room_id = room['_id']

    # Перепланирование авто-удаления
    await reschedule_auto_delete(bot, room_id, rooms_collection)

    await state.clear()
    await message.answer(f"Время жизни комнаты с кодом <code>{message.text}</code> было обновлено.", parse_mode="HTML", reply_markup=default_keyboard)

    logger.info(f"Время жизни комнаты {message.text} с индификатором {room_id} было обновлено пользователем {message.from_user.id}")


@dp.message(Command("start"))
@dp.message(CommandStart(deep_link=True))
async def start(message: types.Message):
    await message.answer(await get_content_file('start'), parse_mode="HTML", reply_markup=default_keyboard)


@dp.message(Command("help"))
async def help(message: types.Message):
    await message.answer(await get_content_file('help'), parse_mode="HTML", reply_markup=default_keyboard)


@dp.message(Command("rules"))
async def rules(message: types.Message):
    await message.answer(await get_content_file('rules_1'), parse_mode="HTML")
    await message.answer(await get_content_file('rules_2'), parse_mode="HTML", reply_markup=default_keyboard)


@dp.message(Command("list"))
async def list_rooms_command(message: types.Message):
    await list_rooms(message)


@dp.message(F.text.casefold() == "список рум")
async def list_rooms_text(message: types.Message):
    await list_rooms(message)


async def list_rooms(message: types.Message):
    rooms_count = rooms_collection.count_documents({})
    rooms = rooms_collection.find()

    if rooms_count == 0:
        await message.answer(AnswerEnum.not_found_rooms.value, parse_mode="HTML")
        return

    output = "<b>Румы, где ты можешь поиграть:</b>\n\n"
    for i, room_data in enumerate(rooms, start=1):
        room = Room.from_dict(room_data)
        output += (
            f"                           ╭    🚀  {room.map.value}\n"
            f"{i:<3} <code>{room.code}</code>       --  👑    {room.host}\n"
            f"                           ╰   🎲   {room.game_mode.value}\n\n\n"
        )

    output += "Приятной игры 🙂\n\n <span class='tg-spoiler'>И не будь абобой 😉</span>"

    await message.answer(output, parse_mode=ParseMode.HTML, reply_markup=default_keyboard)


@dp.message(Command("add"))
async def add_room(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    user_room = rooms_collection.find_one({'owner_id': user_id})

    if user_room:
        await message.answer(f"У вас уже есть комната с кодом <code>{user_room['code']}</code>.\nХотите удалить её перед добавлением новой?",
                             parse_mode="HTML",
                             reply_markup=create_keyboard(["Да", "Отмена"],
                             include_cancel=False))
        await state.set_state(RoomState.confirm_delete)
    else:
        await message.answer(AnswerEnum.choose_code.value, reply_markup=cancel_keyboard)
        await state.set_state(RoomState.code)


@dp.message(Command("del"))
async def delete_room(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    user_rooms = list(rooms_collection.find({'owner_id': user_id}))

    if not user_rooms:
        await message.answer(AnswerEnum.not_found.value)
        return

    buttons = [types.KeyboardButton(text=room['code']) for room in user_rooms]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 3] for i in range(0, len(buttons), 3)],
        resize_keyboard=True
    )
    keyboard.keyboard.append([types.KeyboardButton(text="Отмена")])

    await message.answer(AnswerEnum.choose_room.value, reply_markup=keyboard)
    await state.set_state(RoomState.delete)


@dp.message(Command("edit"))
async def edit_room(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    user_rooms = list(rooms_collection.find({'owner_id': user_id}))

    if not user_rooms:
        await message.answer(AnswerEnum.not_found.value)
        return

    buttons = [types.KeyboardButton(text=room['code']) for room in user_rooms]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 3] for i in range(0, len(buttons), 3)],
        resize_keyboard=True
    )
    keyboard.keyboard.append([types.KeyboardButton(text="Отмена")])

    await message.answer(AnswerEnum.choose_room.value, reply_markup=keyboard)
    await state.set_state(RoomState.edit)


# Регистрация обработчиков состояния
dp.message.register(process_code, RoomState.code)
dp.message.register(process_host, RoomState.host)
dp.message.register(process_map, RoomState.map)
dp.message.register(process_game_mode, RoomState.game_mode)
dp.message.register(confirm_delete, RoomState.confirm_delete)
dp.message.register(edit_option, RoomState.edit_option)
dp.message.register(edit_code, RoomState.edit_code)
dp.message.register(edit_host, RoomState.edit_host)
dp.message.register(edit_map, RoomState.edit_map)
dp.message.register(edit_game_mode, RoomState.edit_game_mode)
dp.message.register(process_update_room, RoomState.update)


# Запуск бота
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await restore_auto_deletion_tasks(bot, rooms_collection) # Восстановить отслеживания при запуске
    await dp.start_polling(bot)

if __name__ == '__main__':
    logger.info("Запуск бота")
    asyncio.run(main())