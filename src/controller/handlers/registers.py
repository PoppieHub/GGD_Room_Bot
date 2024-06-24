from src.controller.handlers.states_management import process_code, process_host, process_map, process_game_mode, confirm_delete, \
    edit_option, edit_code, edit_host, edit_map, edit_game_mode, process_update_room
from src.controller.handlers.states import RoomState
from src.config import dp


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