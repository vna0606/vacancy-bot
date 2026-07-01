import asyncio
import html
import time
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramRetryAfter

import db
from db import get_active_users, get_fresh_vacancies, disable_user

MAX_PER_USER = 999
CONCURRENCY = 30          # сколько пользователей обрабатываем параллельно
MSG_PER_SEC = 20          # общий лимит Telegram-сообщений в секунду (Telegram допускает ~30/сек в разные чаты)
FLUSH_EVERY = 200         # сколько (tg_id, vacancy_id) пар копим перед батч-записью в sent_notifications

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


class RateLimiter:
    """Держит суммарную частоту вызовов не выше rate_per_sec, независимо от того,
    сколько задач шлют сообщения параллельно."""

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


def _digest_header() -> str:
    from datetime import datetime, timezone, timedelta
    msk = datetime.now(timezone(timedelta(hours=3)))
    date_str = msk.strftime("%-d %B %Y").lower()
    months = {"january": "января", "february": "февраля", "march": "марта", "april": "апреля",
              "may": "мая", "june": "июня", "july": "июля", "august": "августа",
              "september": "сентября", "october": "октября", "november": "ноября", "december": "декабря"}
    for en, ru in months.items():
        date_str = date_str.replace(en, ru)
    return f"📋 <b>Свежая подборка вакансий на {date_str}</b>"


async def _send_with_retry(rate_limiter: RateLimiter, bot: Bot, tg_id: int, text: str, **kwargs):
    while True:
        await rate_limiter.acquire()
        try:
            return await bot.send_message(tg_id, text, **kwargs)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)


async def run_digest(bot_token: str, lookback_hours: int):
    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    rate_limiter = RateLimiter(MSG_PER_SEC)
    semaphore = asyncio.Semaphore(CONCURRENCY)

    sent_buffer: list[tuple[int, int]] = []
    buffer_lock = asyncio.Lock()

    async def flush_buffer(force: bool = False):
        async with buffer_lock:
            if not sent_buffer or not (force or len(sent_buffer) >= FLUSH_EVERY):
                return
            pairs, sent_buffer[:] = list(sent_buffer), []
        # Turso-запрос — вне лока, чтобы не блокировать остальные конкурентные
        # задачи на время сетевого вызова.
        try:
            await db.mark_sent_bulk(pairs)
        except Exception as e:
            # Не роняем asyncio.gather() из-за одного неудачного флаша — иначе
            # оставшиеся пользователи вообще не получат рассылку.
            print(f"[notifier] mark_sent_bulk failed for {len(pairs)} pairs: {e}")

    async def process_user(user: dict, sent_map: dict[int, set[int]], all_vacancies: list[dict]):
        tg_id = user["tg_id"]
        stacks = user.get("stacks") or []
        if not stacks:
            return

        already_sent = sent_map.get(tg_id, set())
        matched = [
            v for v in all_vacancies
            if v["id"] not in already_sent and _vacancy_matches(v, stacks)
        ]
        if not matched:
            return

        to_send = matched[:MAX_PER_USER]
        leftover = len(matched) - len(to_send)

        async with semaphore:
            try:
                await _send_with_retry(rate_limiter, bot, tg_id, _digest_header())

                for v in to_send:
                    await _send_with_retry(
                        rate_limiter, bot, tg_id, _format_vacancy(v), disable_web_page_preview=True,
                    )
                    async with buffer_lock:
                        sent_buffer.append((tg_id, v["id"]))

                if leftover > 0:
                    await _send_with_retry(
                        rate_limiter, bot, tg_id,
                        f"📋 И ещё <b>{leftover}</b> вакансий по твоим стекам — завтра пришлю следующую порцию.",
                    )
                    async with buffer_lock:
                        sent_buffer.extend((tg_id, v["id"]) for v in matched[MAX_PER_USER:])

                print(f"[notifier] tg_id={tg_id} sent={len(to_send)}")

            except TelegramForbiddenError:
                print(f"[notifier] tg_id={tg_id} blocked bot — disabling")
                await disable_user(tg_id, reason="blocked")
            except TelegramBadRequest as e:
                print(f"[notifier] tg_id={tg_id} bad request: {e}")
            except Exception as e:
                # Ошибка одного пользователя не должна ронять asyncio.gather() для остальных.
                print(f"[notifier] tg_id={tg_id} unexpected error: {e}")

        await flush_buffer()

    try:
        users = await get_active_users()
        all_vacancies = await get_fresh_vacancies(lookback_hours)
        sent_map = await db.get_sent_map([v["id"] for v in all_vacancies])
        print(f"[notifier] test_mode={db.TEST_MODE} users={len(users)}, fresh_vacancies={len(all_vacancies)}")

        await asyncio.gather(*(process_user(u, sent_map, all_vacancies) for u in users))
        await flush_buffer(force=True)

    finally:
        await bot.session.close()
        await db.close_client()
