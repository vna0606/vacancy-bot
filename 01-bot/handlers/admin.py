import os
import re
from aiogram import Router, Bot, F
from aiogram.enums import ParseMode
from aiogram.types import Message

router = Router()

ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID", "0"))


@router.message(F.from_user.id == ADMIN_TG_ID)
async def admin_reply(message: Message, bot: Bot):
    # Ответ администратора на пересланное сообщение пользователя
    if not message.reply_to_message:
        return

    original_text = message.reply_to_message.text or ""
    match = re.search(r"\(id:\s*(\d+)\)", original_text)
    if not match:
        return

    user_tg_id = int(match.group(1))
    try:
        await bot.send_message(user_tg_id, message.text)
        await message.react([{"type": "emoji", "emoji": "✅"}])
    except Exception as e:
        await message.answer(f"Не удалось отправить: {e}")


@router.message()
async def catch_all(message: Message, bot: Bot):
    if not ADMIN_TG_ID:
        return

    user = message.from_user
    name = user.full_name or ""
    username = f"@{user.username}" if user.username else "без username"

    await bot.send_message(
        ADMIN_TG_ID,
        f"📩 Сообщение от {name} {username} (id: {user.id}):\n\n«{message.text}»",
        parse_mode=None,
    )
