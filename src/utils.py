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


# Валидация кода комнаты
def validate_code(text):
    return len(text) == 7 and text.isascii() and text.isalnum()


# Валидация имени хоста
def validate_host(text):
    return 2 <= len(text) <= 15 and text.isprintable()


async def get_content_file(name=''):
    path_file = './info/' + name + '.txt'
    try:
        with open(path_file, 'r') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return "Файл не найден"