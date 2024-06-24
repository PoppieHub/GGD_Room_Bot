from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from aiogram import types, F
from aiogram.fsm.context import FSMContext

from src.config import dp, rooms_collection, users_collection
from src.controller.handlers.states import RoomState
from src.keyboards import default_keyboard, cancel_keyboard, create_keyboard
from src.utils import get_content_file
from src.models import Room, AnswerEnum


@dp.message(Command("start"))
@dp.message(CommandStart(deep_link=True))
async def start(message: types.Message):
    user_id = message.from_user.id
    user_data = users_collection.find_one({"user_id": user_id})

    await message.answer(await get_content_file('start'), parse_mode=ParseMode.HTML, reply_markup=default_keyboard)

    # Добавляем пользователя в словарь
    if user_data is None:
        users_collection.insert_one({
            'username': message.from_user.username,
            'chat_id': message.chat.id
        })


@dp.message(Command("help"))
async def help(message: types.Message):
    await message.answer(await get_content_file('help'), parse_mode=ParseMode.HTML, reply_markup=default_keyboard)


@dp.message(Command("rules"))
async def rules(message: types.Message):
    await message.answer(await get_content_file('rules_1'), parse_mode=ParseMode.HTML)
    await message.answer(await get_content_file('rules_2'), parse_mode=ParseMode.HTML, reply_markup=default_keyboard)


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
        await message.answer(AnswerEnum.not_found_rooms.value, parse_mode=ParseMode.HTML)
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
                             parse_mode=ParseMode.HTML,
                             reply_markup=create_keyboard(["Да", "Отмена"],
                             include_cancel=False))
        await state.set_state(RoomState.confirm_delete)
    else:
        await message.answer(AnswerEnum.choose_code.value, reply_markup=cancel_keyboard, parse_mode=ParseMode.HTML)
        await state.set_state(RoomState.code)


@dp.message(Command("del"))
async def delete_room(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    user_rooms = list(rooms_collection.find({'owner_id': user_id}))

    if not user_rooms:
        await message.answer(AnswerEnum.not_found.value, parse_mode=ParseMode.HTML)
        return

    buttons = [types.KeyboardButton(text=room['code']) for room in user_rooms]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 3] for i in range(0, len(buttons), 3)],
        resize_keyboard=True
    )
    keyboard.keyboard.append([types.KeyboardButton(text="Отмена")])

    await message.answer(AnswerEnum.choose_room.value, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(RoomState.delete)


@dp.message(Command("edit"))
async def edit_room(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    user_rooms = list(rooms_collection.find({'owner_id': user_id}))

    if not user_rooms:
        await message.answer(AnswerEnum.not_found.value, parse_mode=ParseMode.HTML)
        return

    buttons = [types.KeyboardButton(text=room['code']) for room in user_rooms]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 3] for i in range(0, len(buttons), 3)],
        resize_keyboard=True
    )
    keyboard.keyboard.append([types.KeyboardButton(text="Отмена")])

    await message.answer(AnswerEnum.choose_room.value, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(RoomState.edit)


@dp.message(Command("update"))
async def update_room(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    user_rooms = list(rooms_collection.find({'owner_id': user_id}))

    if not user_rooms:
        await message.answer(AnswerEnum.not_found.value, parse_mode=ParseMode.HTML)
        return

    buttons = [types.KeyboardButton(text=room['code']) for room in user_rooms]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 3] for i in range(0, len(buttons), 3)],
        resize_keyboard=True
    )
    keyboard.keyboard.append([types.KeyboardButton(text="Отмена")])

    await message.answer(AnswerEnum.choose_room.value, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(RoomState.update)