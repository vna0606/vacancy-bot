import os
from aiogram import Router, Bot, F
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from db import get_user, upsert_user, update_notify, update_last_seen, log_event

router = Router()

MAIN_MENU_BUTTON_TEXTS = {
    "⚙️ Настроить стек",
    "🔔 Уведомления",
    "👤 Мой профиль",
    "🔒 Закрытое сообщество",
    "📨 Разместить вакансию",
    "❤️ Поддержать",
}

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⚙️ Настроить стек"), KeyboardButton(text="🔔 Уведомления")],
        [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="📨 Разместить вакансию")],
        [KeyboardButton(text="🔒 Закрытое сообщество"), KeyboardButton(text="❤️ Поддержать")],
    ],
    resize_keyboard=True,
    persistent=True,
)

COMMUNITY_URL = "https://boosty.to/ulbitv?utm_source=vac_bot"


async def is_community_member(bot: Bot, tg_id: int) -> bool:
    chat_id = os.getenv("COMMUNITY_CHAT_ID", "")
    if not chat_id:
        return True
    try:
        member = await bot.get_chat_member(chat_id, tg_id)
        return member.status in ("member", "creator", "administrator", "restricted")
    except Exception as e:
        print(f"[access] check failed for {tg_id}: {e}")
        return False


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, command: CommandObject):
    tg_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or ""
    ref_source = command.args or None  # payload после /start, например "youtube"

    member = await is_community_member(bot, tg_id)

    user = await get_user(tg_id)
    if user is None:
        await upsert_user(tg_id, username, full_name, ref_source)
        await update_notify(tg_id, 1 if member else 0)
        await log_event(tg_id, "start", ref_source or "direct")
    else:
        await upsert_user(tg_id, username, full_name)  # ref_source не перезаписываем
        # Реактивируем если вернулся в чат
        if member and not user.get("notify_enabled", 0):
            await update_notify(tg_id, 1)
        elif not member and user.get("notify_enabled", 0):
            await update_notify(tg_id, 0)
        await log_event(tg_id, "start", "returning_user")
    await update_last_seen(tg_id)

    # Одинаковое приветствие для всех
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Через этот бот ты будешь получать свежие вакансии с контактами "
        "телеграм каждый день. Мы мониторим источники и каждый день тебе "
        "будем присылать подборку под твой стек.\n\n"
        "Нажми *⚙️ Настроить стек*, чтобы выбрать направления 👇",
        reply_markup=MAIN_MENU,
    )


@router.message(F.text == "🔒 Закрытое сообщество")
async def cmd_community(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Перейти в сообщество", url=COMMUNITY_URL)]
    ])
    await message.answer(
        '*🔒 Закрытое сообщество "Технари"*\n\n'
        "IT-сообщество для разработчиков, которые хотят развивать системное мышление, "
        "получать классные офферы и расти по карьерной лестнице.\n"
        "Без мотивационного шума, успешного успеха и бесконечных курсов ради курсов.\n\n"
        "Все подробности по кнопке ниже",
        reply_markup=kb,
    )
