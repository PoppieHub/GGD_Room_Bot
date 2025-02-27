import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient


# Настройка логгирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Добавление FileHandler для записи логов в файл
file_handler = logging.FileHandler('bot.log')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Инициализация токена
TOKEN = dotenv_values(".env")["API_TOKEN"]
ADMIN_ID = dotenv_values(".env")["ADMIN_ID"]
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

mongo_client = AsyncIOMotorClient(
    dotenv_values(".env")["MONGO_CLIENT"],
    tlsAllowInvalidCertificates=True
)
db = mongo_client['ggd']

rooms_collection = db['rooms']
users_collection = db['users']
chats_collection = db['chats']
