import os
import asyncio
import logging
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import config
from database.engine import init_db
from database.requests import cleanup_old_processed_messages
from handlers import channel_setup, subscriber, admin_settings, admin_replies, payments


# Фейковый веб-сервер, чтобы Render дал 100% БЕСПЛАТНЫЙ тариф Web Service ($0)
async def handle_ping(request):
    return web.Response(text="Bot Onward is active 24/7!")


async def start_dummy_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    await init_db()
    await cleanup_old_processed_messages(days=60)

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

    await start_dummy_web_server()

    logging.info("🚀 Бот Onward запущен на Render (Free Web Service 0$)!")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Бот остановлен.")