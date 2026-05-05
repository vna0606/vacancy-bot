import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
NOTIFY_HOUR = int(os.getenv("NOTIFY_HOUR", "9"))
LOOKBACK_HOURS = int(os.getenv("VACANCIES_LOOKBACK_HOURS", "24"))

from sender import run_digest


async def main():
    if "--now" in sys.argv:
        print("[notifier] Running digest now...")
        await run_digest(BOT_TOKEN, LOOKBACK_HOURS)
        print("[notifier] Done.")
        return

    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_digest,
        args=[BOT_TOKEN, LOOKBACK_HOURS],
        trigger="cron",
        hour=NOTIFY_HOUR,
        minute=0,
    )
    scheduler.start()
    print(f"[notifier] Scheduled daily digest at {NOTIFY_HOUR}:00 UTC. Ctrl+C to stop.")
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
