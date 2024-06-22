# Клавиатуры
from src.models import Map, GameMode
from aiogram import types


def create_keyboard(button_texts, row_width=3, include_cancel=True):
    buttons = [types.KeyboardButton(text=text) for text in button_texts]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + row_width] for i in range(0, len(buttons), row_width)],
        resize_keyboard=True
    )
    if include_cancel:
        keyboard.keyboard.append([types.KeyboardButton(text="Отмена")])
    return keyboard


map_keyboard = create_keyboard([m.value for m in Map])
game_mode_keyboard = create_keyboard([gm.value for gm in GameMode])
cancel_keyboard = create_keyboard(["Отмена"], include_cancel=False)
default_keyboard = create_keyboard(["Список рум"], row_width=1, include_cancel=False)