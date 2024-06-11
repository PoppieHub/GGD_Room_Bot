# Клавиатуры
from src.models import Map, GameMode
from src.utils import create_keyboard

map_keyboard = create_keyboard([m.value for m in Map])
game_mode_keyboard = create_keyboard([gm.value for gm in GameMode])
cancel_keyboard = create_keyboard(["Отмена"], include_cancel=False)
default_keyboard = create_keyboard(["Список рум"], row_width=1, include_cancel=False)