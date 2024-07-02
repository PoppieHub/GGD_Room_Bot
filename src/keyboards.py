# Клавиатуры
import logging

from src.models import Map, GameMode, Room, QueryCommand
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


def get_subscribe_keyboard(room: Room, is_subscribed):
    button_text = "Отписаться от хоста" if is_subscribed else "Подписаться на хоста"
    query_text = QueryCommand.unsubscribe.value if is_subscribed else QueryCommand.subscribe.value

    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=button_text, callback_data=f"{query_text.lower()}_{room.code}")]
        ]
    )
