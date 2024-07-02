from src.config import users_collection, chats_collection, rooms_collection
from src.models import User, Chat


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


async def get_user(user_id: int) -> User:
    user = await users_collection.find_one({'user_id': user_id})

    if user is None:
        user_data = User(user_id=user_id).to_dict()
        await users_collection.insert_one(user_data)
        user = await users_collection.find_one({'user_id': user_id})

    return User.from_dict(user)


async def get_chat(chat_id: int) -> Chat:
    chat = await chats_collection.find_one({'chat_id': chat_id})

    if chat is None:
        chat_data = Chat(chat_id=chat_id).to_dict()
        await chats_collection.insert_one(chat_data)
        chat = await chats_collection.find_one({'chat_id': chat_id})

    return Chat.from_dict(chat)


async def update_user_subscriptions(user, chat: Chat, room_code, subscribe=True):
    if subscribe:
        # Проверяем, есть ли уже такой чат в подписках пользователя
        if any(sub.chat_id == chat.chat_id for sub in user.subscribers):
            return

        user.subscribers.append(chat)
    else:
        # Удаляем чат из подписчиков пользователя
        user.subscribers = [sub for sub in user.subscribers if sub.chat_id != chat.chat_id]

    # Обновляем подписчиков пользователя в базе данных
    await users_collection.update_one(
        {'user_id': user.user_id},
        {'$set': {'subscribers': [sub.to_dict() for sub in user.subscribers]}}
    )

    # Обновляем подписчиков владельца комнаты в базе данных
    await rooms_collection.update_one(
        {'code': room_code},
        {'$set': {'owner.subscribers': [sub.to_dict() for sub in user.subscribers]}}
    )

