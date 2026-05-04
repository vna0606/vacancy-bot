import os
from aiogram import Router, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from db import get_user, upsert_user, update_notify

router = Router()

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⚙️ Настроить стек"), KeyboardButton(text="🔔 Уведомления")],
        [KeyboardButton(text="👤 Мой профиль")],
    ],
    resize_keyboard=True,
    persistent=True,
)


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
async def cmd_start(message: Message, bot: Bot):
    tg_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or ""

    member = await is_community_member(bot, tg_id)

    user = await get_user(tg_id)
    if user is None:
        await upsert_user(tg_id, username, full_name)
        await update_notify(tg_id, 1 if member else 0)
    else:
        await upsert_user(tg_id, username, full_name)
        # Реактивируем если вернулся в чат
        if member and not user.get("notify_enabled", 0):
            await update_notify(tg_id, 1)
        elif not member and user.get("notify_enabled", 0):
            await update_notify(tg_id, 0)

    # Одинаковое приветствие для всех
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Через этот бот ты будешь получать свежие вакансии с контактами "
        "телеграм каждый день. Мы мониторим источники и каждый день тебе "
        "будем присылать подборку под твой стек.\n\n"
        "Нажми *⚙️ Настроить стек*, чтобы выбрать направления 👇",
        reply_markup=MAIN_MENU,
    )
