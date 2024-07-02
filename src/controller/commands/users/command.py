import logging

from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from aiogram import types, F
from aiogram.fsm.context import FSMContext

from src.config import dp, rooms_collection
from src.controller.handlers.states import RoomState
from src.keyboards import default_keyboard, cancel_keyboard, create_keyboard, get_subscribe_keyboard
from src.utils import get_content_file, get_user, get_chat, update_user_subscriptions, update_user_rating
from src.models import Room, AnswerEnum, QueryCommand


@dp.message(Command("start"))
@dp.message(CommandStart(deep_link=True))
async def start(message: types.Message):
    await message.answer(await get_content_file('start'), parse_mode=ParseMode.HTML, reply_markup=default_keyboard)
    await get_chat(message.chat.id)


@dp.message(Command("help"))
async def help(message: types.Message):
    await message.answer(await get_content_file('help'), parse_mode=ParseMode.HTML, reply_markup=default_keyboard)


@dp.message(Command("rules"))
async def rules(message: types.Message):
    await message.answer(await get_content_file('rules_1'), parse_mode=ParseMode.HTML)
    await message.answer(await get_content_file('rules_2'), parse_mode=ParseMode.HTML, reply_markup=default_keyboard)


async def subscribe_management(callback_query: types.CallbackQuery, subscribe_action):
    room = await rooms_collection.find_one({"code": callback_query.data.split("_")[1]})
    chat = await get_chat(callback_query.message.chat.id)

    if room is None:
        await callback_query.answer("Запись больше не акутальна, я не смогу провести действие")
        return

    room = Room.from_dict(room)

    await update_user_subscriptions(room.owner, chat, room.code, subscribe_action)

    if subscribe_action:
        await callback_query.answer(f"Вы подписались на обновления хоста с ником {room.host}")
    else:
        await callback_query.answer(f"Вы отписались от обновлений хоста с ником {room.host}")


@dp.callback_query(F.data.startswith(f"{QueryCommand.subscribe.value}_"))
async def subscribe_room(callback_query: types.CallbackQuery):
    await subscribe_management(callback_query, True)


@dp.callback_query(F.data.startswith(f"{QueryCommand.unsubscribe.value}_"))
async def unsubscribe_room(callback_query: types.CallbackQuery):
    await subscribe_management(callback_query, False)


@dp.callback_query(F.data.startswith(f"{QueryCommand.like.value}_"))
async def like_room(callback_query: types.CallbackQuery):
    await update_user_rating(callback_query.from_user.id, callback_query.data.split("_")[1], True)
    await callback_query.answer("Ваша реакция учтена")


@dp.callback_query(F.data.startswith(f"{QueryCommand.dislike.value}_"))
async def dislike_room(callback_query: types.CallbackQuery):
    await update_user_rating(callback_query.from_user.id, callback_query.data.split("_")[1], False)
    await callback_query.answer("Ваша реакция учтена")


@dp.message(Command("list"))
async def list_rooms_command(message: types.Message):
    await list_rooms(message)


@dp.message(F.text.casefold() == "список рум")
async def list_rooms_text(message: types.Message):
    await list_rooms(message)


async def list_rooms(message: types.Message):
    rooms_count = await rooms_collection.count_documents({})
    chat = await get_chat(message.chat.id)

    if rooms_count == 0:
        await message.answer(AnswerEnum.not_found_rooms.value, parse_mode=ParseMode.HTML)
        return

    async for room_data in rooms_collection.find():
        room = Room.from_dict(room_data)
        is_subscribed = chat.chat_id in [chat_item.chat_id for chat_item in room.owner.subscribers]

        # Подсчет лайков и дизлайков
        likes = sum(1 for rating in room.owner.rating if rating.rating)
        dislikes = sum(1 for rating in room.owner.rating if not rating.rating)

        output = f"<i>Рейтинг: 👍 {likes} / 👎 {dislikes}</i>\n\n"
        output += (
            f"                         ╭    🚀  {room.map.value}\n"
            f"<code>{room.code}</code>       --¦     👑  <b>{room.host}</b>\n"
            f"                         ╰    🎲  {room.game_mode.value}"
        )
        await message.answer(output, parse_mode=ParseMode.HTML,
                             reply_markup=get_subscribe_keyboard(room, is_subscribed))


@dp.message(Command("add"))
async def add_room(message: types.Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    user_room = await rooms_collection.find_one({'owner': user.to_dict()})

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
    user = await get_user(message.from_user.id)
    user_rooms_cursor = rooms_collection.find({'owner': user.to_dict()})

    user_rooms = await user_rooms_cursor.to_list(length=None)

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
    user = await get_user(message.from_user.id)
    user_rooms_cursor = rooms_collection.find({'owner': user.to_dict()})

    user_rooms = await user_rooms_cursor.to_list(length=None)

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
    user = await get_user(message.from_user.id)
    user_rooms_cursor = rooms_collection.find({'owner': user.to_dict()})

    user_rooms = await user_rooms_cursor.to_list(length=None)

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