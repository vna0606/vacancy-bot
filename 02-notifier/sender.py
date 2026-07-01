import asyncio
import html
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from db import get_active_users, get_fresh_vacancies, get_sent_ids, mark_sent, disable_user

MAX_PER_USER = 999

# direction — канонический enum из vacancy_formatter.py (01-bot и it-vacancies-base
# используют один и тот же классификатор), поэтому сравниваем точным равенством,
# а не подстрокой: подстрочный поиск по title ловил "QA Fullstack" в FullStack и т.п.
STACK_TO_DIRECTION = {
    "Backend": "backend",
    "Frontend": "frontend",
    "FullStack": "fullstack",
    "Mobile": "mobile",
    "DevOps": "devops",
    "ML/AI": "ml",
    "Data": "data",
    "QA": "qa",
}


def _vacancy_matches(vacancy: dict, stacks: list) -> bool:
    direction = (vacancy.get("direction") or "").lower()
    return any(STACK_TO_DIRECTION.get(stack) == direction for stack in stacks)


def _esc(text: str) -> str:
    return html.escape(text or "")


def _format_vacancy(v: dict) -> str:
    title = _esc(v.get("title") or "Вакансия")
    parts = [f"<b>{title}</b>", ""]

    if v.get("company_name"):
        parts.append(f"<b>Компания:</b> {_esc(v['company_name'])}")
    if v.get("work_format"):
        parts.append(f"<b>Формат:</b> {_esc(v['work_format'])}")
    if v.get("salary"):
        parts.append(f"<b>Уровень ЗП:</b> {_esc(v['salary'])}")

    if v.get("telegraph_url"):
        parts.append("")
        parts.append(f"<b>Описание:</b> {_esc(v['telegraph_url'])}")

    if v.get("recruiter_contact"):
        parts.append("")
        parts.append(f"<b>Связаться с HR:</b> {_esc(v['recruiter_contact'])}")

    return "\n".join(parts)


async def run_digest(bot_token: str, lookback_hours: int):
    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        users = await get_active_users()
        all_vacancies = await get_fresh_vacancies(lookback_hours)
        print(f"[notifier] users={len(users)}, fresh_vacancies={len(all_vacancies)}")

        for user in users:
            tg_id = user["tg_id"]
            stacks = user.get("stacks") or []
            if not stacks:
                continue

            sent_ids = await get_sent_ids(tg_id)
            matched = [
                v for v in all_vacancies
                if v["id"] not in sent_ids and _vacancy_matches(v, stacks)
            ]

            if not matched:
                continue

            to_send = matched[:MAX_PER_USER]
            leftover = len(matched) - len(to_send)

            try:
                from datetime import datetime, timezone, timedelta
                msk = datetime.now(timezone(timedelta(hours=3)))
                date_str = msk.strftime("%-d %B %Y").lower()
                months = {"january":"января","february":"февраля","march":"марта","april":"апреля",
                          "may":"мая","june":"июня","july":"июля","august":"августа",
                          "september":"сентября","october":"октября","november":"ноября","december":"декабря"}
                for en, ru in months.items():
                    date_str = date_str.replace(en, ru)
                await bot.send_message(tg_id, f"📋 <b>Свежая подборка вакансий на {date_str}</b>")
                await asyncio.sleep(0.3)

                for v in to_send:
                    text = _format_vacancy(v)
                    await bot.send_message(tg_id, text, disable_web_page_preview=True)
                    await mark_sent(tg_id, v["id"])
                    await asyncio.sleep(0.3)

                if leftover > 0:
                    await bot.send_message(
                        tg_id,
                        f"📋 И ещё <b>{leftover}</b> вакансий по твоим стекам — завтра пришлю следующую порцию.",
                    )
                    for v in matched[MAX_PER_USER:]:
                        await mark_sent(tg_id, v["id"])

                print(f"[notifier] tg_id={tg_id} sent={len(to_send)}")

            except TelegramForbiddenError:
                print(f"[notifier] tg_id={tg_id} blocked bot — disabling")
                await disable_user(tg_id, reason="blocked")
            except TelegramBadRequest as e:
                print(f"[notifier] tg_id={tg_id} bad request: {e}")

    finally:
        await bot.session.close()
