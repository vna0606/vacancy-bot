import asyncio
import os
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from db import get_active_users, get_fresh_vacancies, get_sent_ids, mark_sent, disable_user

MAX_PER_USER = 999

COMMUNITY_CHAT_ID = os.getenv("COMMUNITY_CHAT_ID", "")

NOT_MEMBER_TEXT = (
    "🔒 Этот бот присылает вакансии только членам нашего закрытого сообщества.\n\n"
    "Чтобы продолжить получать подборки вакансий, продлите свою подписку "
    "и отправьте боту команду /start — после этого вы продолжите получать подборки."
)

STACK_ALIASES = {
    "ML/AI": ["ml", "ai", "machine learning", "deep learning", "nlp", "llm", "data science"],
    "Mobile": ["mobile", "ios", "android", "flutter", "react native", "swift", "kotlin"],
    "FullStack": ["fullstack", "full stack", "full-stack"],
    "DevOps": ["devops", "sre", "infrastructure", "kubernetes", "k8s"],
    "QA": ["qa", "quality assurance", "тестировщик", "тестирование"],
    "PM": ["product manager", "менеджер продукта", "project manager"],
    "Data": ["data", "аналитик", "analyst"],
    "Backend": ["backend", "back-end", "back end"],
    "Frontend": ["frontend", "front-end", "front end"],
}


async def is_community_member(bot: Bot, tg_id: int) -> bool:
    if not COMMUNITY_CHAT_ID:
        return True
    try:
        member = await bot.get_chat_member(COMMUNITY_CHAT_ID, tg_id)
        return member.status in ("member", "creator", "administrator", "restricted")
    except Exception as e:
        print(f"[access] check failed for {tg_id}: {e}")
        return True  # при ошибке API не отключаем пользователя


def _vacancy_matches(vacancy: dict, stacks: list) -> bool:
    direction = (vacancy.get("direction") or "").lower()
    title = (vacancy.get("title") or "").lower()
    text = direction + " " + title

    for stack in stacks:
        if stack.lower() in text:
            return True
        for alias in STACK_ALIASES.get(stack, []):
            if alias in text:
                return True
    return False


def _format_vacancy(v: dict) -> str:
    title = v.get("title") or "Вакансия"
    parts = [f"*{title}*", ""]

    if v.get("company_name"):
        parts.append(f"*Компания:* {v['company_name']}")
    if v.get("work_format"):
        parts.append(f"*Формат:* {v['work_format']}")
    if v.get("salary"):
        parts.append(f"*Уровень ЗП:* {v['salary']}")

    if v.get("telegraph_url"):
        parts.append("")
        parts.append(f"*Описание:* {v['telegraph_url']}")

    if v.get("recruiter_contact"):
        parts.append("")
        parts.append(f"*Связаться с HR:* {v['recruiter_contact']}")

    return "\n".join(parts)


async def run_digest(bot_token: str, lookback_hours: int):
    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    try:
        users = await get_active_users()
        all_vacancies = await get_fresh_vacancies(lookback_hours)
        print(f"[notifier] users={len(users)}, fresh_vacancies={len(all_vacancies)}")

        for user in users:
            tg_id = user["tg_id"]
            stacks = user.get("stacks") or []
            if not stacks:
                continue

            # Проверяем членство в сообществе
            if not await is_community_member(bot, tg_id):
                print(f"[notifier] tg_id={tg_id} not in community — disabling")
                await disable_user(tg_id)
                try:
                    await bot.send_message(tg_id, NOT_MEMBER_TEXT)
                except Exception:
                    pass
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
                await bot.send_message(tg_id, f"📋 *Свежая подборка вакансий на {date_str}*")
                await asyncio.sleep(0.3)

                for v in to_send:
                    text = _format_vacancy(v)
                    await bot.send_message(tg_id, text, disable_web_page_preview=True)
                    await mark_sent(tg_id, v["id"])
                    await asyncio.sleep(0.3)

                if leftover > 0:
                    await bot.send_message(
                        tg_id,
                        f"📋 И ещё *{leftover}* вакансий по твоим стекам — завтра пришлю следующую порцию.",
                    )
                    for v in matched[MAX_PER_USER:]:
                        await mark_sent(tg_id, v["id"])

                print(f"[notifier] tg_id={tg_id} sent={len(to_send)}")

            except TelegramForbiddenError:
                print(f"[notifier] tg_id={tg_id} blocked bot — disabling")
                await disable_user(tg_id)
            except TelegramBadRequest as e:
                print(f"[notifier] tg_id={tg_id} bad request: {e}")

    finally:
        await bot.session.close()
