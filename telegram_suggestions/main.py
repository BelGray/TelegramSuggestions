import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from telegram_suggestions.config import config
from telegram_suggestions.database.engine import init_db
from telegram_suggestions.handlers import channel_setup, subscriber, admin_settings, admin_replies, payments


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    await init_db()

    # Включаем HTML разметку глобально по умолчанию для всего бота
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    dp.include_router(channel_setup.router)
    dp.include_router(subscriber.router)
    dp.include_router(admin_settings.router)
    dp.include_router(admin_replies.router)
    dp.include_router(payments.router)

    logging.info("🚀 Бот Onward успешно запущен и готов к работе (HTML ParseMode)!")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Бот остановлен.")