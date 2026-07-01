"""Разовый анонс для не-членов сообщества о старте рассылки вакансий.
Запуск: python announce_nonmembers.py        — реальная рассылка всем получателям
        python announce_nonmembers.py --test — тестовое сообщение только админу
"""
import asyncio
import os
import sys
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
from db import execute, update_notify
from handlers.start import MAIN_MENU

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID", "0"))

TEXT = (
    "Привет! У нас две отличные новости.\n\n"
    "Мы обновляем бота, чтобы сделать поиск работы и размещение вакансий проще и доступнее.\n\n"
    "*Первая новость:* мы открываем доступ к ежедневным рассылкам вакансий *для всех*! "
    "Раньше этот функционал был доступен только участникам "
    "[закрытого сообщества](https://boosty.to/ulbitv?utm_source=tg_vac_bot&utm_content=post_anons), "
    "но с сегодняшнего дня ты тоже начнёшь получать подборки вакансий по своему стеку прямо в "
    "этот чат.\n\n"
    "Первая подборка придёт уже сегодня в 16:00 по московскому времени. Если хочешь уточнить "
    "направления или проверить настройки — нажми *«⚙️ Настроить стек»* в меню.\n\n"
    "*Вторая новость:* мы автоматизировали подачу вакансий. Теперь, чтобы разместить "
    "объявление, не нужно писать в личку — просто нажми кнопку *«📨 Разместить вакансию»* "
    "прямо здесь, в боте.\n\n"
    "Настраивай фильтры под свой стек и пользуйся обновлённым инструментом!"
)


async def main():
    test_mode = "--test" in sys.argv

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    try:
        if test_mode:
            await bot.send_message(ADMIN_TG_ID, TEXT, reply_markup=MAIN_MENU)
            print(f"[announce] test message sent to admin {ADMIN_TG_ID}")
            return

        result = await execute(
            "SELECT tg_id FROM users WHERE notify_enabled=1 AND community_member=0 "
            "AND stacks != '' AND stacks != '[]'"
        )
        rows = result.get("rows", [])
        tg_ids = [int(row[0]["value"]) for row in rows]
        print(f"[announce] total recipients: {len(tg_ids)}")

        sent = 0
        failed = 0
        for tg_id in tg_ids:
            try:
                await bot.send_message(tg_id, TEXT, reply_markup=MAIN_MENU)
                sent += 1
                await asyncio.sleep(0.05)
            except TelegramForbiddenError:
                print(f"[announce] {tg_id} blocked — disabling")
                await update_notify(tg_id, 0, "blocked")
                failed += 1
            except TelegramBadRequest as e:
                print(f"[announce] {tg_id} bad request: {e}")
                failed += 1
            except Exception as e:
                print(f"[announce] {tg_id} error: {e}")
                failed += 1

        print(f"[announce] done: sent={sent}, failed/blocked={failed}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
