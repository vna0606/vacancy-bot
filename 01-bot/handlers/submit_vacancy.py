import os
import re
import logging
from datetime import datetime, timedelta
from itertools import count
from zoneinfo import ZoneInfo

from aiogram import Router, Bot, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from db import insert_vacancy, find_duplicate_vacancy
from vacancy_filter import classify
from vacancy_llm_filter import classify_uncertain
from vacancy_formatter import format_vacancy
from vacancy_dedup import compute_dedup_key
from telegraph import create_telegraph_page
from .start import MAIN_MENU_BUTTON_TEXTS
from .donate import donate_keyboard

logger = logging.getLogger(__name__)
router = Router()

ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID", "0"))
VACANCY_AUTO_PUBLISH = os.getenv("VACANCY_AUTO_PUBLISH", "0") == "1"
TELEGRAPH_ACCESS_TOKEN = os.getenv("TELEGRAPH_ACCESS_TOKEN", "")
TELEGRAPH_AUTHOR_NAME = os.getenv("TELEGRAPH_AUTHOR_NAME", "IT Вакансии")


class SubmitVacancy(StatesGroup):
    waiting_text = State()
    confirm = State()


SUPPORT_TEXT = (
    "Мы публикуем вакансии бесплатно и не берём денег за размещение.\n\n"
    "Если хочешь поддержать развитие бота — будем благодарны 🙏"
)

REJECT_TEXT = (
    "❌ Это не похоже на техническую IT-вакансию с контактом для отклика.\n\n"
    "Мы размещаем только технические вакансии (разработка, QA, DevOps, Data/ML, аналитика и т.д.) "
    "с указанным контактом в Telegram для отклика."
)


def _duplicate_text(existing: dict) -> str:
    link = f"\n👉 {existing['telegraph_url']}" if existing.get("telegraph_url") else ""
    return (
        f"⚠️ Похоже, такая вакансия уже размещалась недавно:{link}\n\n"
        "Мы публикуем одну и ту же вакансию не чаще раза в неделю — попробуй прислать её снова "
        "через несколько дней."
    )

CANCEL_KB = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="❌ Отмена", callback_data="vac_submit_cancel")
]])

# Дайджест уходит по будням в NOTIFY_HOUR=13 UTC = 16:00 МСК (02-notifier/notifier.py).
# Заявки, одобренные до 15:00 МСК того же рабочего дня, успевают в этот заход;
# остальные — в следующий рабочий день (с учётом выходных).
MOSCOW_TZ = ZoneInfo("Europe/Moscow")
_PUBLISH_CUTOFF_HOUR = 15
_WEEKDAY_PHRASES = {
    0: "в понедельник", 1: "во вторник", 2: "в среду",
    3: "в четверг", 4: "в пятницу",
}


def _publish_eta_text() -> str:
    now = datetime.now(MOSCOW_TZ)
    cutoff = now.replace(hour=_PUBLISH_CUTOFF_HOUR, minute=0, second=0, microsecond=0)
    if now.weekday() < 5 and now < cutoff:
        return (
            "✅ Вакансия одобрена!\n\n"
            "Сегодня она попадёт в рассылку бота (~16:00 МСК) и в канал (~17:00 МСК)."
        )
    next_day = now + timedelta(days=1)
    while next_day.weekday() >= 5:
        next_day += timedelta(days=1)
    phrase = _WEEKDAY_PHRASES[next_day.weekday()]
    return (
        "✅ Вакансия одобрена!\n\n"
        "Заявки после 15:00 МСК (и в выходные) попадают в следующий рабочий день — "
        f"вы увидите её в боте и в канале {phrase} (~16:00 и ~17:00 МСК)."
    )

# submission_id -> {tg_id, title, category, direction, summary, telegraph_url}
# В памяти процесса — тот же подход, что у admin_bot.py в it-vacancies-base.
_submission_seq = count(1)
_pending_moderation: dict[int, dict] = {}


def _extract_summary(content: str) -> dict:
    """Вычленяет короткие поля карточки из оформленного текста вакансии."""
    s = {"company": "", "format": "", "salary": "", "employment": "", "hr_contact": ""}
    for line in content.split("\n"):
        line = line.strip()
        for key, pattern in (
            ("company", r"^Компания:\s*(.*)"),
            ("format", r"^Формат:\s*(.*)"),
            ("salary", r"^Уровень ЗП:\s*(.*)"),
            ("employment", r"^Занятость:\s*(.*)"),
        ):
            m = re.match(pattern, line, re.IGNORECASE)
            if m:
                s[key] = m.group(1).strip()
                break
        if "@" in line and not s["hr_contact"]:
            m = re.search(r"@\S+", line)
            if m:
                s["hr_contact"] = m.group(0)
    return s


def _card_text(title: str, s: dict, telegraph_url: str) -> str:
    contact = (s["hr_contact"] or "не указан").replace("_", "\\_")
    return (
        f"*{title}*\n\n"
        f"*Компания:* {s['company'] or 'не указана'}\n"
        f"*Формат:* {s['format'] or 'не указан'}\n"
        f"*Уровень ЗП:* {s['salary'] or 'не указана'}\n"
        f"*Занятость:* {s['employment'] or 'не указана'}\n\n"
        f"*Описание:* {telegraph_url}\n\n"
        f"*Связаться с HR:* {contact}"
    )


@router.message(F.text == "📨 Разместить вакансию")
async def btn_submit_vacancy(message: Message, state: FSMContext):
    await state.set_state(SubmitVacancy.waiting_text)
    await message.answer(
        "Мы размещаем только технические IT-вакансии.\n\n"
        "Чтобы разместить вакансию, пришли её текст в одном сообщении — обязательно укажи "
        "контакт в Telegram (@username или t.me/...) для отклика.",
        reply_markup=CANCEL_KB,
    )


@router.callback_query(F.data == "vac_submit_cancel")
async def cb_cancel_waiting(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Отменено.")
    await callback.answer()


async def _notify_admin_error(bot: Bot, user, stage: str, reason: str):
    if not ADMIN_TG_ID:
        return
    username = f"@{user.username}" if user.username else "без username"
    try:
        await bot.send_message(
            ADMIN_TG_ID,
            f"⚠️ Не удалось обработать вакансию ({stage})\n"
            f"Пользователь: {user.full_name} {username} (id: {user.id})\n"
            f"Причина: {reason}",
        )
    except Exception as e:
        logger.warning("Failed to notify admin about vacancy error: %s", e)


@router.message(SubmitVacancy.waiting_text)
async def handle_vacancy_text(message: Message, state: FSMContext, bot: Bot):
    if message.text in MAIN_MENU_BUTTON_TEXTS:
        await state.clear()
        await message.answer("Размещение вакансии отменено. Нажми нужную кнопку ещё раз 👇")
        return

    if message.content_type != "text":
        await message.answer("Пришли вакансию текстом, пожалуйста.")
        return

    text = message.text
    label, reason = classify(text, sender_username=message.from_user.username)
    logger.info("vacancy_filter tg_id=%s label=%s reason=%s", message.from_user.id, label, reason)

    if label == "uncertain":
        label = await classify_uncertain(text)

    if label == "irrelevant":
        await state.clear()
        await message.answer(REJECT_TEXT)
        return

    processing_msg = await message.answer("⏳ Обрабатываю вакансию…")

    result, format_error = await format_vacancy(text)
    if result is None:
        await processing_msg.edit_text("❌ Ошибка обработки. Попробуй прислать вакансию ещё раз позже.")
        await _notify_admin_error(bot, message.from_user, "LLM-форматирование", format_error)
        return
    if not result.get("is_vacancy"):
        await state.clear()
        await processing_msg.edit_text("❌ Текст не распознан как вакансия.")
        return

    title = result["title"]
    content = result["content"]
    category = result.get("category", "other")
    direction = result.get("direction", "other")
    summary = _extract_summary(content)

    dedup_key = compute_dedup_key(summary["company"], summary["hr_contact"], title)
    existing = await find_duplicate_vacancy(dedup_key)
    if existing:
        await state.clear()
        await processing_msg.edit_text(_duplicate_text(existing), disable_web_page_preview=True)
        return

    telegraph_url, telegraph_error = await create_telegraph_page(
        title=title,
        content_text=content,
        access_token=TELEGRAPH_ACCESS_TOKEN,
        author_name=TELEGRAPH_AUTHOR_NAME,
    )
    if not telegraph_url:
        await processing_msg.edit_text("❌ Не удалось подготовить описание вакансии. Попробуй ещё раз позже.")
        await _notify_admin_error(bot, message.from_user, "создание Telegraph-страницы", telegraph_error)
        return

    await state.update_data(
        title=title, category=category, direction=direction,
        summary=summary, telegraph_url=telegraph_url, dedup_key=dedup_key,
    )
    await state.set_state(SubmitVacancy.confirm)

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Опубликовать", callback_data="vac_submit_yes"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="vac_submit_no"),
    ]])
    await processing_msg.edit_text(
        _card_text(title, summary, telegraph_url) + "\n\nВсё верно? Отправить на публикацию?",
        reply_markup=kb,
        disable_web_page_preview=True,
    )


@router.callback_query(SubmitVacancy.confirm, F.data == "vac_submit_no")
async def cb_submit_no(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Отменено.")
    await callback.answer()


@router.callback_query(SubmitVacancy.confirm, F.data == "vac_submit_yes")
async def cb_submit_yes(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()
    await callback.answer()

    title = data["title"]
    category = data["category"]
    direction = data["direction"]
    summary = data["summary"]
    telegraph_url = data["telegraph_url"]
    dedup_key = data["dedup_key"]

    if VACANCY_AUTO_PUBLISH:
        await insert_vacancy(
            title=title, company=summary["company"], hr_contact=summary["hr_contact"],
            salary=summary["salary"], work_format=summary["format"],
            telegraph_url=telegraph_url, direction=direction, category=category,
            dedup_key=dedup_key,
        )
        await callback.message.edit_text(
            _card_text(title, summary, telegraph_url)
            + "\n\n✅ Вакансия сохранена, попадёт в следующую рассылку.",
            disable_web_page_preview=True,
        )
        await callback.message.answer(SUPPORT_TEXT, reply_markup=donate_keyboard())
        return

    submission_id = next(_submission_seq)
    _pending_moderation[submission_id] = {
        "tg_id": callback.from_user.id,
        "title": title, "category": category, "direction": direction,
        "summary": summary, "telegraph_url": telegraph_url, "dedup_key": dedup_key,
    }

    await callback.message.edit_text(
        _card_text(title, summary, telegraph_url) + "\n\n📨 Отправлено на модерацию.",
        disable_web_page_preview=True,
    )

    if ADMIN_TG_ID:
        mod_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"vac_mod_approve:{submission_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"vac_mod_reject:{submission_id}"),
        ]])
        await bot.send_message(
            ADMIN_TG_ID,
            f"🆕 Вакансия от пользователя (id: {callback.from_user.id}):\n\n"
            + _card_text(title, summary, telegraph_url),
            reply_markup=mod_kb,
            disable_web_page_preview=True,
        )


@router.callback_query(F.data.startswith("vac_mod_approve:"), F.from_user.id == ADMIN_TG_ID)
async def cb_mod_approve(callback: CallbackQuery, bot: Bot):
    submission_id = int(callback.data.split(":", 1)[1])
    data = _pending_moderation.pop(submission_id, None)
    if data is None:
        await callback.answer("Заявка уже обработана.")
        return

    summary = data["summary"]
    await insert_vacancy(
        title=data["title"], company=summary["company"], hr_contact=summary["hr_contact"],
        salary=summary["salary"], work_format=summary["format"],
        telegraph_url=data["telegraph_url"], direction=data["direction"], category=data["category"],
        dedup_key=data["dedup_key"],
    )
    card = _card_text(data["title"], summary, data["telegraph_url"])
    await callback.message.edit_text(card + "\n\n✅ Одобрено", disable_web_page_preview=True)
    await callback.answer("Сохранено")
    try:
        await bot.send_message(data["tg_id"], _publish_eta_text())
        await bot.send_message(data["tg_id"], SUPPORT_TEXT, reply_markup=donate_keyboard())
    except Exception as e:
        logger.warning("Failed to notify submitter %s: %s", data["tg_id"], e)


@router.callback_query(F.data.startswith("vac_mod_reject:"), F.from_user.id == ADMIN_TG_ID)
async def cb_mod_reject(callback: CallbackQuery, bot: Bot):
    submission_id = int(callback.data.split(":", 1)[1])
    data = _pending_moderation.pop(submission_id, None)
    if data is None:
        await callback.answer("Заявка уже обработана.")
        return

    card = _card_text(data["title"], data["summary"], data["telegraph_url"])
    await callback.message.edit_text(card + "\n\n❌ Отклонено", disable_web_page_preview=True)
    await callback.answer("Отклонено")
    try:
        await bot.send_message(data["tg_id"], "❌ К сожалению, вакансия не прошла модерацию.")
    except Exception as e:
        logger.warning("Failed to notify submitter %s: %s", data["tg_id"], e)
