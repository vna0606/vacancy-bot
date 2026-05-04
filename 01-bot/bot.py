import asyncio
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

from handlers import start, stacks, settings

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
NOTIFY_HOUR = int(os.getenv("NOTIFY_HOUR", "9"))

NOTIFIER_SCRIPT = os.path.join(os.path.dirname(__file__), '..', '02-notifier', 'notifier.py')


async def run_digest():
    print("[scheduler] Running daily digest...")
    proc = await asyncio.create_subprocess_exec(
        sys.executable, NOTIFIER_SCRIPT, "--now",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    if stdout:
        print(stdout.decode())
    print(f"[scheduler] Digest done, exit code: {proc.returncode}")


async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(stacks.router)
    dp.include_router(settings.router)

    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        lambda: asyncio.create_task(run_digest()),
        trigger="cron",
        day_of_week="mon-fri",
        hour=NOTIFY_HOUR,
        minute=0,
    )
    scheduler.start()
    print(f"[bot] Started. Daily digest scheduled at {NOTIFY_HOUR}:00 UTC")

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()


if __name__ == '__main__':
    asyncio.run(main())
