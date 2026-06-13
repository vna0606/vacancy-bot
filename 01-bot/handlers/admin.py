import os
import re
import json
from collections import Counter
from pathlib import Path
from aiogram import Router, Bot, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message

from db import execute

router = Router()

ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID", "0"))
MESSAGES_LOG = Path(__file__).parent.parent / "messages.log"


def _log_incoming(message: Message):
    user = message.from_user
    entry = {
        "ts": message.date.isoformat() if message.date else None,
        "tg_id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "type": message.content_type,
        "text": message.text,
        "caption": message.caption,
    }
    if message.sticker:
        entry["sticker_emoji"] = message.sticker.emoji
    if message.document:
        entry["file_name"] = message.document.file_name
    with open(MESSAGES_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


@router.message(Command("stats"), F.from_user.id == ADMIN_TG_ID)
async def admin_stats(message: Message):
    result = await execute("SELECT stacks, notify_enabled FROM users")
    rows = result.get("rows", [])

    total = len(rows)
    active = 0
    no_stacks = 0
    direction_counter = Counter()
    all_direction_counter = Counter()

    for row in rows:
        stacks_raw, notify_enabled = (v["value"] if v["type"] != "null" else None for v in row)
        try:
            stacks = json.loads(stacks_raw) if stacks_raw else []
        except Exception:
            stacks = []

        if not stacks:
            no_stacks += 1

        all_direction_counter.update(stacks)

        if str(notify_enabled) == "1" and stacks:
            active += 1
            direction_counter.update(stacks)

    percent = round(active / total * 100) if total else 0

    lines = [
        "📊 Статистика бота",
        "",
        f"👥 Всего пользователей: {total}",
        f"🔔 Получают рассылку: {active} ({percent}%)",
        f"🚫 Не указали направление: {no_stacks}",
        "",
        "Разбивка по направлениям (получают рассылку):",
    ]
    for direction, count in direction_counter.most_common():
        lines.append(f"{direction} — {count}")

    lines += ["", "Разбивка по направлениям (все пользователи):"]
    for direction, count in all_direction_counter.most_common():
        lines.append(f"{direction} — {count}")

    await message.answer("\n".join(lines), parse_mode=None)


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

    _log_incoming(message)

    user = message.from_user
    name = user.full_name or ""
    username = f"@{user.username}" if user.username else "без username"

    await bot.send_message(
        ADMIN_TG_ID,
        f"📩 Сообщение от {name} {username} (id: {user.id}):",
        parse_mode=None,
    )
    await bot.forward_message(
        chat_id=ADMIN_TG_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )
