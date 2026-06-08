import os
import json
import asyncio
from collections import Counter
from datetime import datetime, timedelta, timezone

import httpx
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

from db import execute

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID", "0"))


async def main():
    result = await execute("SELECT stacks, notify_enabled, created_at FROM users")
    rows = result.get("rows", [])

    total = len(rows)
    active = 0
    new_users = 0
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

    for row in rows:
        stacks_raw, notify_enabled, created_at = (
            v["value"] if v["type"] != "null" else None for v in row
        )
        try:
            stacks = json.loads(stacks_raw) if stacks_raw else []
        except Exception:
            stacks = []

        if str(notify_enabled) == "1" and stacks:
            active += 1

        if created_at and created_at >= week_ago:
            new_users += 1

    percent = round(active / total * 100) if total else 0

    text = (
        "📈 Еженедельная динамика\n"
        "\n"
        f"🆕 Новых пользователей за неделю: {new_users}\n"
        f"👥 Всего пользователей: {total}\n"
        f"🔔 Получают рассылку: {active} ({percent}%)"
    )

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_TG_ID, "text": text},
        )
        resp.raise_for_status()


if __name__ == "__main__":
    asyncio.run(main())
