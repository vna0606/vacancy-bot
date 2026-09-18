"""Разовая рассылка статьи о мошенниках с обновлённым меню.

Запуск теста только администратору:
    python announce_scam_safety.py --test

Боевая отправка всем активным пользователям требует двух явных флагов:
    python announce_scam_safety.py --send --confirm-production
"""

import argparse
import asyncio
import os
import time

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from dotenv import load_dotenv


load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from db import execute, update_notify
from handlers.scam_safety import ARTICLE_URL
from handlers.start import MAIN_MENU


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID", "0"))
CONCURRENCY = 30
MSG_PER_SEC = 20

TEXT = (
    "Друзья, привет! Снова вынуждены вернуться к теме мошенников — в последнее время "
    "появилось несколько новых изощренных схем, с помощью которых пытаются обмануть "
    "соискателей.\n\n"
    "Мы обновили нашу статью и собрали там все актуальные способы скама: от классической "
    "кражи данных и манипуляций с банками до фальшивых агентств и опасных схем с "
    "оформлением ИП.\n\n"
    f"👉 [Читать статью со всеми актуальными схемами]({ARTICLE_URL})\n\n"
    "Чтобы эта информация всегда была под рукой, мы добавили ее в меню бота. Теперь "
    "статья со всеми схемами и правилами безопасности доступна по кнопке "
    "«⚠️ Про мошенников».\n\n"
    "Будем постоянно дополнять этот материал. Если вы сами сталкивались с новыми схемами "
    "или подозрительными «работодателями» — пишите нам в личку @ulbitv\\_vac, чтобы "
    "предупредить остальных и обезопасить сообщество.\n\n"
    "Берегите себя и проверяйте компании до того, как отправлять документы или "
    "подписывать офферы."
)

class RateLimiter:
    def __init__(self, rate_per_sec: float):
        self._interval = 1.0 / rate_per_sec
        self._lock = asyncio.Lock()
        self._next_time = time.monotonic()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            wait = self._next_time - now
            if wait > 0:
                await asyncio.sleep(wait)
                self._next_time += self._interval
            else:
                self._next_time = now + self._interval


async def send_with_retry(limiter: RateLimiter, bot: Bot, tg_id: int, reply_markup):
    while True:
        await limiter.acquire()
        try:
            await bot.send_message(
                tg_id,
                TEXT,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
            return
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)


async def get_recipients() -> list[int]:
    result = await execute("SELECT tg_id FROM users WHERE notify_enabled = 1")
    return [int(row[0]["value"]) for row in result.get("rows", [])]


async def main():
    args = parse_args()
    if not BOT_TOKEN or not ADMIN_TG_ID:
        raise RuntimeError("TELEGRAM_BOT_TOKEN и ADMIN_TG_ID должны быть заданы")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    limiter = RateLimiter(MSG_PER_SEC)
    try:
        if args.test:
            await send_with_retry(limiter, bot, ADMIN_TG_ID, MAIN_MENU)
            print(f"[scam-safety] test sent only to admin {ADMIN_TG_ID}")
            return

        recipients = await get_recipients()
        print(f"[scam-safety] preview recipients={len(recipients)}")
        if not args.send:
            print("[scam-safety] preview only; nothing sent")
            return
        if not args.confirm_production:
            raise RuntimeError("Для боевой рассылки нужен флаг --confirm-production")

        semaphore = asyncio.Semaphore(CONCURRENCY)
        sent = 0
        failed = 0
        counter_lock = asyncio.Lock()

        async def process(tg_id: int):
            nonlocal sent, failed
            async with semaphore:
                try:
                    await send_with_retry(limiter, bot, tg_id, MAIN_MENU)
                    async with counter_lock:
                        sent += 1
                except TelegramForbiddenError:
                    await update_notify(tg_id, 0, "blocked")
                    async with counter_lock:
                        failed += 1
                except TelegramBadRequest as exc:
                    print(f"[scam-safety] tg_id={tg_id} bad request: {exc}")
                    async with counter_lock:
                        failed += 1
                except Exception as exc:
                    print(f"[scam-safety] tg_id={tg_id} error: {exc}")
                    async with counter_lock:
                        failed += 1

        await asyncio.gather(*(process(tg_id) for tg_id in recipients))
        print(f"[scam-safety] done sent={sent} failed/blocked={failed}")
    finally:
        await bot.session.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--test", action="store_true")
    mode.add_argument("--send", action="store_true")
    parser.add_argument("--confirm-production", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main())
