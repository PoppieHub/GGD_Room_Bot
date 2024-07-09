from src.config import users_collection, chats_collection, rooms_collection
from src.models import User, Chat, Rating, Room


# Валидация кода комнаты
def validate_code(text):
    return len(text) == 6 and text.isascii() and text.isalnum()


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


async def update_user_rating(user_id: int, room_code: str, is_like: bool):
    room_data = await rooms_collection.find_one({'code': room_code})
    if room_data is None:
        return

    room = Room.from_dict(room_data)
    owner = await get_user(room.owner.user_id)

    # Проверяем, существует ли уже реакция от этого пользователя
    existing_rating = next((r for r in owner.rating if r.user_id == user_id), None)

    if existing_rating:
        existing_rating.rating = is_like
    else:
        rating = Rating(is_like, user_id)
        owner.rating.append(rating)

    # Обновляем данные в базе данных
    await users_collection.update_one(
        {'user_id': owner.user_id},
        {'$set': {'rating': [rating.to_dict() for rating in owner.rating]}}
    )

    await rooms_collection.update_one(
        {'code': room_code},
        {'$set': {'owner.rating': [rating.to_dict() for rating in owner.rating]}}
    )
