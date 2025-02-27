from functools import wraps
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram import types
from aiogram.fsm.context import FSMContext

from src.controller.handlers.states import AdminState
from src.utils import get_content_file
from src.config import dp, logger, ADMIN_ID, rooms_collection, users_collection
from src.keyboards import default_keyboard, cancel_keyboard
from src.models import AnswerEnum, User


async def is_admin(user_id: int):
    admin_data = await users_collection.find_one({'user_id': user_id})

    if (admin_data and User.from_dict(admin_data).is_admin) or user_id == ADMIN_ID:
        return True

    return False


def is_root(user_id: int):
    if str(user_id) != ADMIN_ID:
        return False

    return True


# Декоратор-обертка для проверки прав
def wrapper_root(handler):
    @wraps(handler)
    async def wrapper(message: types.Message, *args, **kwargs):
        is_root_result = is_root(message.from_user.id)
        if is_root_result:
            return await handler(message, *args, **kwargs)
        else:
            is_admin_result = await is_admin(message.from_user.id)
            if is_admin_result:
                logger.info(f"Пользователь {message.from_user.id} является администратором")
                return await handler(message, *args, **kwargs)
            else:
                logger.warning(f"Пользователь {message.from_user.id} не имеет прав администратора")
                await message.answer(AnswerEnum.you_dont_have_root.value, parse_mode=ParseMode.HTML,
                                     reply_markup=default_keyboard)

    return wrapper


@dp.message(Command("admin_help"))
@wrapper_root
async def admin_help(message: types.Message):
    await message.answer(await get_content_file('admin_help'), parse_mode=ParseMode.HTML, reply_markup=default_keyboard)


@dp.message(Command("add_admin"))
@wrapper_root
async def add_admin(message: types.Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте id пользователя, которого вы хотите назначить администратором.", reply_markup=cancel_keyboard)
    await state.set_state(AdminState.add_admin)


@dp.message(Command("list_admins"))
@wrapper_root
async def list_admins(message: types.Message):
    output = "<b>Список администраторов:</b>\n\n"
    i = 1
    async for users_data in users_collection.find({'is_admin': True}):
        admin = User.from_dict(users_data)
        output += (
            f"{i} <code>{admin.user_id}</code>\n"
        )
        i += 1

    await message.answer(output, parse_mode=ParseMode.HTML, reply_markup=default_keyboard)


@dp.message(Command("del_admin"))
@wrapper_root
async def del_admin(message: types.Message, state: FSMContext):
    users_cursor = users_collection.find({'is_admin': True})
    admins = await users_cursor.to_list(length=None)

    # Преобразование данных и создание кнопок
    buttons = [types.KeyboardButton(text=str(admin['user_id'])) for admin in admins]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 3] for i in range(0, len(buttons), 3)],
        resize_keyboard=True
    )
    keyboard.keyboard.append([types.KeyboardButton(text="Отмена")])

    await message.answer(
        "Пожалуйста, отправьте id пользователя, которого вы хотите удалить из администраторов.",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminState.del_admin)


@dp.message(Command("admin_del"))
@wrapper_root
async def admin_delete_room(message: types.Message, state: FSMContext):
    rooms_cursor = rooms_collection.find()
    rooms = await rooms_cursor.to_list(length=None)

    if not rooms:
        await message.answer(AnswerEnum.not_found.value, parse_mode=ParseMode.HTML)
        return

    buttons = [types.KeyboardButton(text=room['code']) for room in rooms]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 3] for i in range(0, len(buttons), 3)],
        resize_keyboard=True
    )
    keyboard.keyboard.append([types.KeyboardButton(text="Отмена")])

    await message.answer(AnswerEnum.choose_room.value, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(AdminState.delete_room)


@dp.message(Command("broadcast"))
@wrapper_root
async def broadcast_message(message: types.Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте сообщение, которое будет отправлено пользователям", reply_markup=cancel_keyboard)
    await state.set_state(AdminState.broadcast_text)
