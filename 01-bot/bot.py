import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

from handlers import start, stacks, settings, submit_vacancy, admin, donate
from db import init_analytics_schema

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(submit_vacancy.router)
    dp.include_router(stacks.router)
    dp.include_router(settings.router)
    dp.include_router(donate.router)
    dp.include_router(admin.router)

    await init_analytics_schema()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
