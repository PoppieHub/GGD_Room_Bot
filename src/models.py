from enum import Enum
from datetime import datetime


class Map(Enum):
    THE_CARNIVAL = "Карнавал"
    EAGLETON_SPRINGS = "Иглтон Спрингс"
    BLOODHAVEN = "Кровавая Гавань"
    ANCIENT_SANDS = "Древняя Пустыня"
    THE_BASEMENT = "Подвал"
    JUNGLE_TEMPLE = "Храм Джунглей"
    GOOSECHAPEL = "Гусчэпл"
    MALLARD_MANOR = "Усадьба Крякв"
    NEXUS_COLONY = "Колония Нексус"
    BLACK_SWAN = "Черный Лебедь"
    SS_MOTHER_GOOSE = "К.К. Матушка Гусыня"
    OTHER = "Разные"


class GameMode(Enum):
    CLASSIC = "Classic"
    DRAFT = "Draft"
    CORRUPTION_MODE = "Corruption Mode"
    GOOSE_HUNT = "Goose Hunt"
    DINE_AND_DASH = "Dine and Dash"
    TRICK_OR_TREAT = "Trick or Treat"
    HANGING_OUT = "Hanging Out"
    TASTES_LIKE_CHICKEN = "Tastes Like Chicken"
    WOW_AND_LOCK = "Ух и ищи"
    OTHER = "Разные"


class ChooseEditEnum(Enum):
    code = "Код"
    host = "Хоста"
    map = "Карту"
    game_mode = "Режим"


class AnswerEnum(Enum):
    we_have_cancel = "У нас отмена!"
    error_code = "<b>Ошибка при вводе.</b> \n\nПожалуйста, введите 7-значный код комнаты"
    error_host = "<b>Ошибка при вводе.</b> \n\nПожалуйста, введите имя хоста (не более 15 символов):"
    choose_code = "Введите код комнаты"
    choose_host = "Введите имя хоста:"
    choose_map = "Выберите карту:"
    choose_game_mode = "Выберите режим игры:"
    choose_edit = "Выберите что изменить:"
    choose_room = "Выберите комнату:"
    info_added_room = "Комната добавлена успешно!"
    not_found = "Увы... Нет подходящей румы 😢"
    not_found_rooms = "Упс...\n\nНет опубликованных рум 😢"
    success_edit = "Изменения приняты!"
    error_edit = "Изменения не приянты, попробуй что-то исправить 😢"
    room_delite = "Комната удалена."
    room_delite_plus = "Комната удалена.\n\nТеперь вы можете добавить новую."
    invalid_option = "Пожалуйста, выберите один из предложенных вариантов или нажмите 'Отмена'."
    you_dont_have_root = "У вас нет прав для использования этой команды."


class Room:
    def __init__(self, code: str, host: str, map: Map, game_mode: GameMode, owner_id: str, created_at=None):
        self.code = code.upper().strip()
        self.host = host.strip()
        self.map = map
        self.game_mode = game_mode
        self.owner_id = owner_id
        self.created_at = created_at or datetime.now()

    def to_dict(self):
        return {
            'code': self.code,
            'host': self.host,
            'map': self.map.value,
            'game_mode': self.game_mode.value,
            'owner_id': self.owner_id,
            'created_at': self.created_at
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            code=data['code'],
            host=data['host'],
            map=Map(data['map']),
            game_mode=GameMode(data['game_mode']),
            owner_id=data['owner_id'],
            created_at=data['created_at']
        )


class Admin:
    def __init__(self, user_id: int):
        self.user_id = user_id

    def to_dict(self):
        return {
            'user_id': self.user_id
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            user_id=data['user_id']
        )