from aiogram.filters.state import State, StatesGroup


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
