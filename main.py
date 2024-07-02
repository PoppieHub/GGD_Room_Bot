from src.tasks import restore_auto_deletion_tasks

from src.controller.include import *


# Запуск бота
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await restore_auto_deletion_tasks(bot, rooms_collection) # Восстановить отслеживания при запуске
    await dp.start_polling(bot)

if __name__ == '__main__':
    logger.info("Запуск бота")
    asyncio.run(main())
