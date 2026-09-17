"""Разовая рассылка предупреждения получателям конкретной Frontend-вакансии.

По умолчанию команда работает в режиме предпросмотра. Для реальной отправки нужен
флаг --send; при TEST_MODE=0 дополнительно требуется --confirm-production.
"""

import argparse
import asyncio
import html
import json
import os

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from dotenv import load_dotenv

import db
from sender import MSG_PER_SEC, RateLimiter, _send_with_retry


load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


def build_message(vacancy_url: str) -> str:
    safe_url = html.escape(vacancy_url, quote=True)
    return (
        "Ребята, мы ранее опубликовали "
        f'<a href="{safe_url}">эту вакансию</a>. '
        "К сожалению, она оказалась мошеннической — пожалуйста, не откликайтесь на неё "
        "и не передавайте никаких данных; удалить уже отправленное сообщение мы не можем, "
        "поэтому предупреждаем вас отдельно."
    )


async def get_vacancy(vacancy_url: str) -> dict:
    result = await db.execute(
        "SELECT id, title, direction FROM vacancies WHERE telegraph_url = ? LIMIT 1",
        [vacancy_url],
    )
    rows = db._rows_to_dicts(result)
    if not rows:
        raise RuntimeError("Вакансия с такой ссылкой не найдена в таблице vacancies")
    vacancy = rows[0]
    vacancy["id"] = int(vacancy["id"])
    if (vacancy.get("direction") or "").lower() != "frontend":
        raise RuntimeError(
            f"Направление вакансии — {vacancy.get('direction')!r}, ожидалось 'frontend'"
        )
    return vacancy


async def get_recipients(vacancy_id: int) -> list[int]:
    sql = (
        "SELECT DISTINCT u.tg_id, u.stacks "
        "FROM users u "
        "JOIN sent_notifications s ON s.user_tg_id = u.tg_id "
        "WHERE s.vacancy_id = ? AND u.notify_enabled = 1"
    )
    args = [vacancy_id]
    if db.TEST_MODE:
        sql += " AND u.tg_id = ?"
        args.append(db.ADMIN_TG_ID)

    rows = db._rows_to_dicts(await db.execute(sql, args))
    recipients = []
    for row in rows:
        try:
            stacks = json.loads(row.get("stacks") or "[]")
        except (TypeError, json.JSONDecodeError):
            continue
        if "Frontend" in stacks:
            recipients.append(int(row["tg_id"]))
    return recipients


async def run(vacancy_url: str, send: bool, confirm_production: bool) -> None:
    vacancy = await get_vacancy(vacancy_url)
    recipients = await get_recipients(vacancy["id"])
    message = build_message(vacancy_url)

    print(f"vacancy_id={vacancy['id']} title={vacancy.get('title')!r}")
    print(f"test_mode={db.TEST_MODE} recipients={len(recipients)}")
    print("\nТекст сообщения:\n")
    print(message)

    if not send:
        print("\nПредпросмотр завершён: сообщения не отправлялись.")
        return
    if not db.TEST_MODE and not confirm_production:
        raise RuntimeError(
            "Для боевой рассылки с TEST_MODE=0 нужен флаг --confirm-production"
        )
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    limiter = RateLimiter(MSG_PER_SEC)
    sent = 0
    try:
        for tg_id in recipients:
            try:
                await _send_with_retry(
                    limiter,
                    bot,
                    tg_id,
                    message,
                    disable_web_page_preview=True,
                )
                sent += 1
            except TelegramForbiddenError:
                await db.disable_user(tg_id, reason="blocked")
                print(f"tg_id={tg_id}: бот заблокирован, уведомления отключены")
            except TelegramBadRequest as exc:
                print(f"tg_id={tg_id}: Telegram отклонил сообщение: {exc}")
            except Exception as exc:
                print(f"tg_id={tg_id}: ошибка отправки: {exc}")
    finally:
        await bot.session.close()
        await db.close_client()

    print(f"Рассылка завершена: отправлено {sent} из {len(recipients)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vacancy-url", required=True)
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--confirm-production", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args.vacancy_url, args.send, args.confirm_production))
