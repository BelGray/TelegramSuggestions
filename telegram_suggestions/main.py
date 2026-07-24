import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from config import config
from database.engine import init_db
from handlers import channel_setup, subscriber, admin_settings, admin_replies, payments


async def main():
    # Настройка логов
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    # Инициализация SQLite базы данных
    await init_db()

    # Инициализация Бота и Диспетчера
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    # Регистрация роутеров хэндлеров
    dp.include_router(channel_setup.router)
    dp.include_router(subscriber.router)
    dp.include_router(admin_settings.router)
    dp.include_router(admin_replies.router)
    dp.include_router(payments.router)

    logging.info("🚀 Бот Onward успешно запущен и готов к работе!")

    # Удаляем вебхуки и запускаем поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Бот остановлен.")