# Валидация кода комнаты
def validate_code(text):
    return len(text) == 7 and text.isascii() and text.isalnum()


# Валидация имени хоста
def validate_host(text):
    return 2 <= len(text) <= 15 and text.isprintable()


async def get_content_file(name='', path_name='./info/', extension='.txt'):
    path_file = path_name + name + extension
    try:
        with open(path_file, 'r') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return "Файл не найден"